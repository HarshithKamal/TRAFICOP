"""
TRAFICOP - Core utilities: data loading, model loading, and inference.
All file paths are relative to the app root so it works both locally and on
Streamlit Cloud / Render / HF Spaces without modification.
"""
import os
import json
import pickle
import numpy as np
import pandas as pd
import xgboost as xgb
import streamlit as st

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")

CAUSE_LABELS = {
    "vehicle_breakdown": "Vehicle Breakdown",
    "accident": "Accident",
    "pot_holes": "Pot Holes",
    "construction": "Construction",
    "water_logging": "Water Logging",
    "tree_fall": "Tree Fall",
    "congestion": "Congestion",
    "public_event": "Public Event",
    "procession": "Procession",
    "vip_movement": "VIP Movement",
    "protest": "Protest",
    "road_conditions": "Road Conditions",
    "others": "Others",
    "debris": "Debris",
    "test_demo": "Test / Demo",
    "fog_low_visibility": "Fog / Low Visibility",
}

RISK_COLORS = {
    "Critical": "#E63946",
    "High": "#F77F00",
    "Medium": "#F2C14E",
    "Low": "#06A77D",
}

CORRIDOR_DIVERSIONS = {
    'Mysore Road': ['Magadi Road', 'Old Madras Road via Ring Road'],
    'Bellary Road 1': ['Bellary Road 2', 'Hennur Main Road'],
    'Bellary Road 2': ['Bellary Road 1', 'IRR(Thanisandra road)'],
    'Tumkur Road': ['Magadi Road', 'West of Chord Road'],
    'Hosur Road': ['Bannerghata Road', 'ORR East 1'],
    'ORR North 1': ['ORR North 2', 'Bellary Road 1'],
    'ORR North 2': ['ORR North 1', 'Hennur Main Road'],
    'ORR East 1': ['ORR East 2', 'Old Airport Road'],
    'ORR East 2': ['ORR East 1', 'Varthur Road'],
    'ORR West 1': ['West of Chord Road', 'Magadi Road'],
    'Old Madras Road': ['Hennur Main Road', 'ORR North 2'],
    'Magadi Road': ['Tumkur Road', 'Mysore Road'],
    'Bannerghata Road': ['Hosur Road', 'ORR East 1'],
    'West of Chord Road': ['Tumkur Road', 'ORR West 1'],
    'CBD 1': ['CBD 2', 'Old Madras Road'],
    'CBD 2': ['CBD 1', 'Old Airport Road'],
    'Hennur Main Road': ['Old Madras Road', 'ORR North 2'],
    'IRR(Thanisandra road)': ['Bellary Road 2', 'ORR North 1'],
    'Varthur Road': ['ORR East 2', 'Old Airport Road'],
    'Old Airport Road': ['CBD 2', 'ORR East 1'],
    'Airport New South Road': ['Bellary Road 1', 'Bellary Road 2'],
    'Non-corridor': ['Nearest major corridor (manual assessment required)'],
}


def get_time_period(h):
    if h is None or (isinstance(h, float) and np.isnan(h)):
        return "unknown"
    h = int(h)
    if 7 <= h < 11:
        return "morning_peak"
    if 11 <= h < 16:
        return "midday"
    if 16 <= h < 20:
        return "evening_peak"
    if 20 <= h < 24:
        return "night"
    return "late_night"


def classify_risk(score):
    if score >= 75:
        return "Critical"
    if score >= 55:
        return "High"
    if score >= 35:
        return "Medium"
    return "Low"


def get_diversion_routes(corridor):
    return CORRIDOR_DIVERSIONS.get(corridor, ["No predefined diversion - manual assessment required"])


@st.cache_data
def get_corridor_centroids(events_df: pd.DataFrame):
    """Average lat/long per corridor, used to call the live Mappls distance API."""
    return events_df.dropna(subset=["latitude", "longitude"]).groupby("corridor")[["latitude", "longitude"]].mean()


def get_diversion_routes_live(corridor, source_lat, source_lng, events_df: pd.DataFrame):
    """
    Returns diversion candidates ranked by live Mappls driving ETA when a Mappls
    API key is configured. Falls back to the static corridor-based list (in the
    same order) when Mappls isn't configured or a call fails, so this is always
    safe to call.

    Returns a list of dicts: [{"corridor": str, "eta_minutes": float|None, "distance_km": float|None}, ...]
    """
    from utils.mappls_client import is_configured, get_distance_eta

    candidates = get_diversion_routes(corridor)
    if not is_configured():
        return [{"corridor": c, "eta_minutes": None, "distance_km": None} for c in candidates]

    centroids = get_corridor_centroids(events_df)
    results = []
    for c in candidates:
        if c not in centroids.index:
            results.append({"corridor": c, "eta_minutes": None, "distance_km": None})
            continue
        target_lat, target_lng = centroids.loc[c]
        eta = get_distance_eta(source_lat, source_lng, target_lat, target_lng)
        if eta and eta.get("duration_s") is not None:
            results.append({
                "corridor": c,
                "eta_minutes": round(eta["duration_s"] / 60, 1),
                "distance_km": round(eta["distance_m"] / 1000, 1) if eta.get("distance_m") else None,
            })
        else:
            results.append({"corridor": c, "eta_minutes": None, "distance_km": None})

    # Rank by ETA when available (None values sort last), preserving original order as tiebreak
    results.sort(key=lambda r: (r["eta_minutes"] is None, r["eta_minutes"] if r["eta_minutes"] is not None else 0))
    return results


def recommend_resources(risk_level, event_cause, requires_closure):
    base_rules = {
        "Critical": {"officers": 4, "barricades": 6, "escalation": "Yes - notify DCP"},
        "High": {"officers": 3, "barricades": 4, "escalation": "Yes - notify Inspector"},
        "Medium": {"officers": 2, "barricades": 2, "escalation": "No"},
        "Low": {"officers": 1, "barricades": 0, "escalation": "No"},
    }
    rec = base_rules[risk_level].copy()
    if requires_closure:
        rec["barricades"] += 2

    tow_causes = {"accident", "vehicle_breakdown"}
    rec["tow_vehicle"] = "Yes" if (event_cause in tow_causes and risk_level in ["Critical", "High", "Medium"]) else "No"

    heavy_equipment_causes = {"water_logging", "tree_fall", "construction", "pot_holes"}
    rec["heavy_equipment_required"] = "Yes" if event_cause in heavy_equipment_causes else "No"
    return rec


@st.cache_resource
def load_model():
    model = xgb.XGBRegressor()
    model.load_model(os.path.join(MODELS_DIR, "resolution_time_model.json"))
    return model


@st.cache_resource
def load_encoders():
    with open(os.path.join(MODELS_DIR, "label_encoders.pkl"), "rb") as f:
        return pickle.load(f)


@st.cache_resource
def load_shap_explainer():
    """
    Builds the SHAP TreeExplainer fresh from the already-loaded XGBoost model,
    rather than unpickling a saved explainer object. A pickled SHAP explainer
    embeds the XGBoost booster's internal binary state, which is NOT guaranteed
    to be compatible across different XGBoost versions/platforms (pickling here
    vs. loading on your machine can be on different XGBoost builds). The model's
    own .json file uses XGBoost's stable, version-safe serialization format, so
    rebuilding the explainer from that avoids the "input stream corrupted" error
    entirely and is also instant - tree explainers are cheap to construct.
    """
    import shap
    model = load_model()
    return shap.TreeExplainer(model)


@st.cache_resource
def load_feature_metadata():
    with open(os.path.join(MODELS_DIR, "feature_metadata.json"), "r") as f:
        return json.load(f)


@st.cache_resource
def load_historical_lookups():
    with open(os.path.join(MODELS_DIR, "historical_lookups.json"), "r") as f:
        return json.load(f)


@st.cache_data
def load_events():
    df = pd.read_csv(os.path.join(DATA_DIR, "processed_events.csv"))
    df["start_datetime"] = pd.to_datetime(df["start_datetime"], errors="coerce", utc=True)
    df["source"] = "historical"
    return df


@st.cache_data
def load_corridor_tri():
    return pd.read_csv(os.path.join(DATA_DIR, "corridor_tri.csv"))


# ---------------------------------------------------------------------------
# Live (session-only) incident store.
#
# Incidents created in the Incident Simulator are kept in st.session_state for
# the current browser session only - they are NOT written to disk, so a page
# reload or new session starts fresh. This is intentional: it lets the
# Simulator's output actually flow through the rest of the dashboard (map,
# KPIs, analytics) for a live demo, without needing a database or any
# persistence layer for a 24-hour build.
# ---------------------------------------------------------------------------

LIVE_INCIDENTS_KEY = "live_incidents"


def init_live_incidents():
    """Call once near the top of app.py so the store always exists before any page reads it."""
    if LIVE_INCIDENTS_KEY not in st.session_state:
        st.session_state[LIVE_INCIDENTS_KEY] = []


def add_live_incident(row: dict):
    """Appends one fully-formed event row (same schema as processed_events.csv) to the session store."""
    init_live_incidents()
    st.session_state[LIVE_INCIDENTS_KEY].append(row)


def get_live_incidents_df() -> pd.DataFrame:
    """Returns the session's live incidents as a DataFrame with the same columns as load_events()."""
    init_live_incidents()
    cols = list(load_events().columns)
    if not st.session_state[LIVE_INCIDENTS_KEY]:
        return pd.DataFrame(columns=cols)
    live_df = pd.DataFrame(st.session_state[LIVE_INCIDENTS_KEY])
    live_df["start_datetime"] = pd.to_datetime(live_df["start_datetime"], errors="coerce", utc=True)
    # ensure column order/presence matches historical data exactly
    for c in cols:
        if c not in live_df.columns:
            live_df[c] = None
    return live_df[cols]


def clear_live_incidents():
    st.session_state[LIVE_INCIDENTS_KEY] = []


def get_combined_events() -> pd.DataFrame:
    """
    Historical events + this session's simulated live incidents, concatenated.
    Every page should call this instead of load_events() directly so simulated
    incidents actually show up across the Map, KPIs, and Analytics pages.
    """
    historical = load_events()
    live = get_live_incidents_df()
    if len(live) == 0:
        return historical
    return pd.concat([historical, live], ignore_index=True)


def build_live_event_row(event_cause, priority, corridor, event_type, requires_closure,
                          hour, dayofweek, month, lat, lng, zone, prediction_result, incident_id):
    """
    Builds one fully-formed row matching processed_events.csv's schema from a
    predict_incident() result, ready to hand to add_live_incident().
    """
    import datetime
    rec = prediction_result["recommendations"]
    now = datetime.datetime.now(datetime.timezone.utc)

    return {
        "id": incident_id,
        "event_type": event_type,
        "event_cause": event_cause,
        "latitude": lat,
        "longitude": lng,
        "endlatitude": None,
        "endlongitude": None,
        "corridor": corridor,
        "priority": priority,
        "zone": zone,
        "status": "active",
        "start_datetime": now.isoformat(),
        "requires_road_closure": bool(requires_closure),
        "hour": hour,
        "dayofweek": dayofweek,
        "is_weekend": 1 if dayofweek in [5, 6] else 0,
        "month": month,
        "time_period": get_time_period(hour),
        "corridor_freq": None,
        "cause_freq": None,
        "corridor_cause_hist_median": None,
        "resolution_minutes": None,  # unresolved - it's a brand new simulated incident
        "impact_score": prediction_result["impact_score"],
        "risk_level": prediction_result["risk_level"],
        "officers": rec["officers"],
        "barricades": rec["barricades"],
        "tow_vehicle": rec["tow_vehicle"],
        "heavy_equipment_required": rec["heavy_equipment_required"],
        "escalation": rec["escalation"],
        "suggested_diversions": ", ".join(prediction_result["suggested_diversions"]) if isinstance(prediction_result["suggested_diversions"], list) else prediction_result["suggested_diversions"],
        "source": "live",
    }


def predict_incident(event_cause, priority, corridor, event_type, requires_closure,
                      hour, dayofweek, month, zone="Unknown Zone"):
    """
    Full inference pipeline for a new/simulated incident.
    Mirrors the exact feature engineering used in the training notebook.
    """
    model = load_model()
    encoders = load_encoders()
    meta = load_feature_metadata()
    lookups = load_historical_lookups()

    cat_features = meta["cat_features"]
    feature_cols = meta["feature_cols"]

    time_period = get_time_period(hour)
    is_weekend = 1 if dayofweek in [5, 6] else 0

    row = {
        "event_type": event_type, "event_cause": event_cause, "priority": priority,
        "corridor": corridor, "zone": zone, "time_period": time_period,
        "requires_road_closure": requires_closure,
    }

    enc_row = {}
    for c in cat_features:
        le = encoders[c]
        val = str(row[c])
        if val in list(le.classes_):
            enc_row[c + "_enc"] = int(le.transform([val])[0])
        else:
            enc_row[c + "_enc"] = 0  # unseen category fallback

    enc_row["hour"] = hour
    enc_row["dayofweek"] = dayofweek
    enc_row["is_weekend"] = is_weekend
    enc_row["month"] = month
    enc_row["corridor_freq"] = lookups["corridor_freq_map"].get(corridor, 0.01)
    enc_row["cause_freq"] = lookups["cause_freq_map"].get(event_cause, 0.01)

    key = f"{corridor}||{event_cause}"
    enc_row["corridor_cause_hist_median"] = lookups["corridor_cause_hist_median"].get(
        key, lookups["overall_median_resolution"]
    )

    X_new = pd.DataFrame([enc_row])[feature_cols]
    pred_log = model.predict(X_new)[0]
    pred_minutes = float(np.expm1(pred_log))

    cs = lookups["cause_severity_map"].get(event_cause, 0.5)
    pw = lookups["priority_weight_map"].get(priority, 0.4)
    cw = lookups["corridor_congestion_proneness"].get(corridor, 0.1)
    clw = 1 if requires_closure else 0
    raw = cs * 45 + pw * 25 + cw * 15 + clw * 15
    rmin, rmax = lookups["impact_score_min"], lookups["impact_score_max"]
    impact = (raw - rmin) / (rmax - rmin) * 100
    impact = max(0, min(100, impact))

    risk = classify_risk(impact)
    rec = recommend_resources(risk, event_cause, requires_closure)
    diversions = get_diversion_routes(corridor)

    return {
        "predicted_resolution_minutes": round(pred_minutes, 1),
        "impact_score": round(impact, 1),
        "risk_level": risk,
        "recommendations": rec,
        "suggested_diversions": diversions,
        "X_new": X_new,
        "enc_row": enc_row,
    }
