import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import shap

from utils.core import load_model, load_encoders, load_feature_metadata, load_shap_explainer, CAUSE_LABELS


def render(events_df: pd.DataFrame, tri_df: pd.DataFrame):
    st.title("🔍 SHAP Explainability")
    st.caption("Understand exactly why the model predicts a given resolution time")

    model = load_model()
    encoders = load_encoders()
    meta = load_feature_metadata()
    explainer = load_shap_explainer()

    feature_cols = meta["feature_cols"]
    cat_features = meta["cat_features"]
    num_features = meta["num_features"]

    st.subheader("Global Feature Importance")
    st.caption("Which features drive resolution-time predictions across all incidents, on average")

    importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=True)
    readable_names = {
        "corridor_cause_hist_median_enc": "Historical median (corridor x cause)",
        "corridor_cause_hist_median": "Historical median (corridor x cause)",
        "cause_freq": "Event cause frequency",
        "requires_road_closure_enc": "Requires road closure",
        "time_period_enc": "Time of day period",
        "zone_enc": "Police zone",
        "event_type_enc": "Planned vs Unplanned",
        "month": "Month",
        "hour": "Hour of day",
        "dayofweek": "Day of week",
        "corridor_freq": "Corridor frequency",
        "priority_enc": "Priority (High/Low)",
        "event_cause_enc": "Event cause",
        "corridor_enc": "Corridor",
        "is_weekend": "Is weekend",
    }
    importances.index = [readable_names.get(i, i) for i in importances.index]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(importances.index, importances.values, color="#2E86AB")
    ax.set_xlabel("Importance")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    st.info(
        "**Historical median (corridor x cause)** dominates — meaning the single strongest signal for "
        "'how long will this take to resolve' is simply: how long have similar incidents on this exact "
        "corridor historically taken? This matches real-world traffic operations intuition."
    )

    st.divider()
    st.subheader("Explain a Specific Prediction")
    st.caption("Pick a real incident from the dataset and see exactly which features pushed its predicted resolution time up or down")

    sample_df = events_df[events_df["resolution_minutes"].notna()].dropna(subset=["corridor", "event_cause"]).copy()
    sample_df = sample_df[(sample_df["resolution_minutes"] > 0) & (sample_df["resolution_minutes"] <= 10080)]

    if len(sample_df) == 0:
        st.warning("No resolved incidents available to explain.")
        return

    idx_options = sample_df.sample(min(50, len(sample_df)), random_state=1).index.tolist()
    selected_idx = st.selectbox(
        "Select an incident",
        idx_options,
        format_func=lambda i: f"#{i} — {CAUSE_LABELS.get(sample_df.loc[i,'event_cause'], sample_df.loc[i,'event_cause'])} on {sample_df.loc[i,'corridor']} ({sample_df.loc[i,'priority']} priority)",
    )

    row = sample_df.loc[selected_idx]

    enc_row = {}
    for c in cat_features:
        le = encoders[c]
        val = str(row[c])
        enc_row[c + "_enc"] = int(le.transform([val])[0]) if val in list(le.classes_) else 0
    for c in num_features:
        enc_row[c] = row[c]

    X_explain = pd.DataFrame([enc_row])[feature_cols]
    shap_vals = explainer.shap_values(X_explain)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(f"**Event Cause:** {CAUSE_LABELS.get(row['event_cause'], row['event_cause'])}")
        st.markdown(f"**Corridor:** {row['corridor']}")
        st.markdown(f"**Priority:** {row['priority']}")
        st.markdown(f"**Actual Resolution Time:** {row['resolution_minutes']:.0f} min")
        pred_log = model.predict(X_explain)[0]
        pred_min = np.expm1(pred_log)
        st.markdown(f"**Model Predicted Resolution Time:** {pred_min:.0f} min")

    with col2:
        shap_series = pd.Series(shap_vals[0], index=[readable_names.get(c, c) for c in feature_cols])
        shap_series = shap_series.sort_values()
        colors = ["#E63946" if v > 0 else "#06A77D" for v in shap_series.values]
        fig2, ax2 = plt.subplots(figsize=(7, 5))
        ax2.barh(shap_series.index, shap_series.values, color=colors)
        ax2.axvline(0, color="black", linewidth=0.8)
        ax2.set_xlabel("SHAP value (impact on log resolution time)")
        fig2.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)
        st.caption("🔴 Red = pushes resolution time UP. 🟢 Green = pushes resolution time DOWN.")
