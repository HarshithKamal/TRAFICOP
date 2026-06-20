import streamlit as st
import pandas as pd
import random
from streamlit_folium import st_folium

from utils.core import (
    predict_incident, CAUSE_LABELS, RISK_COLORS, get_time_period,
    get_diversion_routes_live, add_live_incident, build_live_event_row,
)
from utils.map_builder import build_simulator_map
from utils.mappls_client import is_configured as mappls_is_configured


def render(events_df: pd.DataFrame, tri_df: pd.DataFrame):
    st.title("🧪 Incident Simulator")
    st.caption("Enter a hypothetical incident and get full AI-powered operational recommendations instantly")
    st.info(
        "💡 Submitting an incident here adds it to the **Bengaluru Command Map**, **Executive KPIs**, and "
        "**Analytics** for the rest of your current session (shown with a red pulsing star marker on the map). "
        "It resets when you reload the app — nothing is saved permanently."
    )

    corridors = sorted(events_df["corridor"].dropna().unique())
    causes = sorted(events_df["event_cause"].dropna().unique())

    col1, col2 = st.columns(2)
    with col1:
        event_cause = st.selectbox("Event Cause", causes, format_func=lambda c: CAUSE_LABELS.get(c, c))
        priority = st.selectbox("Priority", ["High", "Low"])
        corridor = st.selectbox("Corridor", corridors)
        event_type = st.selectbox("Event Type", ["unplanned", "planned"])

    with col2:
        requires_closure = st.checkbox("Requires Road Closure?")
        hour = st.slider("Hour of Day", 0, 23, 9)
        dayofweek = st.selectbox(
            "Day of Week", list(range(7)),
            format_func=lambda d: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][d],
        )
        month = st.slider("Month", 1, 12, 6)

    st.caption(f"Time period bucket: **{get_time_period(hour).replace('_', ' ').title()}**")

    if st.button("🚦 Run TRAFICOP Analysis", type="primary", use_container_width=True):
        result = predict_incident(
            event_cause=event_cause, priority=priority, corridor=corridor,
            event_type=event_type, requires_closure=requires_closure,
            hour=hour, dayofweek=dayofweek, month=month,
        )

        # ---- Resolve a location for this simulated incident ----
        corridor_rows = events_df[events_df["corridor"] == corridor].dropna(subset=["latitude", "longitude"])
        if len(corridor_rows) > 0:
            base_lat = corridor_rows["latitude"].mean()
            base_lon = corridor_rows["longitude"].mean()
            zone = corridor_rows["zone"].mode().iloc[0] if "zone" in corridor_rows and not corridor_rows["zone"].isna().all() else "Unknown Zone"
        else:
            base_lat, base_lon = 12.9716, 77.5946  # Bengaluru center fallback
            zone = "Unknown Zone"

        # Small random jitter (~within a few hundred meters) so repeated simulations
        # on the same corridor don't stack exactly on top of each other on the map.
        sim_lat = base_lat + random.uniform(-0.004, 0.004)
        sim_lon = base_lon + random.uniform(-0.004, 0.004)

        incident_id = f"SIM-{len(st.session_state.get('live_incidents', [])) + 1:03d}"
        live_row = build_live_event_row(
            event_cause=event_cause, priority=priority, corridor=corridor,
            event_type=event_type, requires_closure=requires_closure,
            hour=hour, dayofweek=dayofweek, month=month,
            lat=sim_lat, lng=sim_lon, zone=zone,
            prediction_result=result, incident_id=incident_id,
        )
        add_live_incident(live_row)

        st.divider()
        risk = result["risk_level"]
        color = RISK_COLORS.get(risk, "#808080")

        st.success(f"✅ Incident **{incident_id}** added to the live Command Map and dashboard for this session.")

        c1, c2, c3 = st.columns(3)
        c1.metric("Predicted Resolution Time", f"{result['predicted_resolution_minutes']:.0f} min")
        c2.metric("Impact Score", f"{result['impact_score']:.1f} / 100")
        c3.markdown(f"### Risk Level: <span style='color:{color}'>{risk}</span>", unsafe_allow_html=True)

        st.divider()
        col_rec, col_map = st.columns([1, 1])

        with col_rec:
            st.subheader("📋 Recommendations")
            rec = result["recommendations"]
            st.markdown(f"**Officers Required:** {rec['officers']}")
            st.markdown(f"**Barricades Required:** {rec['barricades']}")
            st.markdown(f"**Tow Vehicle Required:** {rec['tow_vehicle']}")
            st.markdown(f"**Heavy Equipment Required:** {rec['heavy_equipment_required']}")
            st.markdown(f"**Escalation:** {rec['escalation']}")

            st.subheader("🔀 Suggested Diversion Routes")
            if mappls_is_configured() and len(corridor_rows) > 0:
                live_routes = get_diversion_routes_live(corridor, base_lat, base_lon, events_df)
                for r in live_routes:
                    if r["eta_minutes"] is not None:
                        st.markdown(f"- **{r['corridor']}** — {r['eta_minutes']:.0f} min, {r['distance_km']:.1f} km (live Mappls ETA)")
                    else:
                        st.markdown(f"- {r['corridor']}")
            else:
                for route in result["suggested_diversions"]:
                    st.markdown(f"- {route}")

        with col_map:
            st.subheader("📍 Location Context")
            end_lat = corridor_rows["endlatitude"].mean() if len(corridor_rows) > 0 and "endlatitude" in corridor_rows else None
            end_lon = corridor_rows["endlongitude"].mean() if len(corridor_rows) > 0 and "endlongitude" in corridor_rows else None
            sim_map = build_simulator_map(sim_lat, sim_lon, end_lat, end_lon, risk, corridor)
            st_folium(sim_map, width=None, height=350, returned_objects=[], key=f"sim_map_{incident_id}")

        if risk in ["Critical", "High"]:
            st.error(f"⚠️ **{risk} risk incident** — immediate dispatch recommended per escalation protocol above.")
        else:
            st.success(f"✅ {risk} risk — standard response protocol applies.")

        st.caption("👉 Switch to **Bengaluru Command Map** or **Executive KPIs** in the sidebar to see this incident reflected live.")
