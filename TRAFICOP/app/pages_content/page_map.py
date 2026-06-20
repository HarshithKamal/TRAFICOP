import streamlit as st
import pandas as pd
from streamlit_folium import st_folium

from utils.core import CAUSE_LABELS
from utils.map_builder import build_command_map


def render(events_df: pd.DataFrame, tri_df: pd.DataFrame):
    st.title("🗺️ Bengaluru Command Map")
    st.caption("Real-time corridor-level traffic command center — live incident overlay")

    with st.expander("🎛️ Map Filters", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            risk_filter = st.multiselect(
                "Risk Level", ["Critical", "High", "Medium", "Low"],
                default=["Critical", "High", "Medium", "Low"],
            )
        with c2:
            cause_options = sorted(events_df["event_cause"].dropna().unique())
            cause_filter = st.multiselect(
                "Event Cause", cause_options,
                default=cause_options,
                format_func=lambda c: CAUSE_LABELS.get(c, c),
            )
        with c3:
            status_filter = st.multiselect(
                "Status", sorted(events_df["status"].dropna().unique()),
                default=sorted(events_df["status"].dropna().unique()),
            )

    filtered = events_df[
        events_df["risk_level"].isin(risk_filter)
        & events_df["event_cause"].isin(cause_filter)
        & events_df["status"].isin(status_filter)
    ]

    col_map, col_legend = st.columns([4, 1])

    with col_legend:
        st.markdown("##### Legend")
        st.markdown("🔴 **Critical**")
        st.markdown("🟠 **High**")
        st.markdown("🟡 **Medium**")
        st.markdown("🟢 **Low**")
        st.markdown("⭐ **Live simulated incident** (pulsing)")
        st.divider()
        st.markdown("##### Layers")
        st.caption("Use the layer control (top-right of map) to toggle:")
        st.caption("• Incidents (clustered)")
        st.caption("• 🔴 Live Simulated Incidents")
        st.caption("• Incident Density Heatmap")
        st.caption("• Corridor TRI Layer")
        st.caption("• Base map style")
        st.divider()
        st.metric("Showing", f"{len(filtered):,} incidents")

    with col_map:
        if len(filtered) == 0:
            st.warning("No incidents match the current filters.")
        else:
            fmap = build_command_map(filtered, tri_df, max_markers=1500)
            st_folium(fmap, width=None, height=620, returned_objects=[])

    st.info(
        "💡 Click any marker to see full incident details: Event Cause, Type, Corridor, Priority, "
        "Resolution Time, Impact Score, Risk Level, Officers Required, Barricades Required, "
        "Tow Vehicle Requirement, and Suggested Diversion Route."
    )
