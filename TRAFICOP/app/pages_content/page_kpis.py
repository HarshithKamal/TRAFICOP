import streamlit as st
import pandas as pd
import plotly.express as px

from utils.core import CAUSE_LABELS, RISK_COLORS


def render(events_df: pd.DataFrame, tri_df: pd.DataFrame):
    st.title("📊 Executive KPIs")
    st.caption("Bengaluru-wide traffic incident overview — ASTraM dataset")

    live_count = (events_df.get("source", pd.Series(dtype=str)) == "live").sum() if "source" in events_df.columns else 0
    if live_count > 0:
        st.success(f"🔴 {live_count} live simulated incident{'s' if live_count != 1 else ''} from this session included below")

    total_events = len(events_df)
    active_events = (events_df["status"] == "active").sum()
    critical_events = (events_df["risk_level"] == "Critical").sum()
    avg_resolution = events_df["resolution_minutes"].dropna()
    avg_resolution = avg_resolution[(avg_resolution > 0) & (avg_resolution <= 10080)].median()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Incidents", f"{total_events:,}")
    col2.metric("Currently Active", f"{active_events:,}")
    col3.metric("Critical Risk Incidents", f"{critical_events:,}")
    col4.metric("Median Resolution Time", f"{avg_resolution:.0f} min" if pd.notna(avg_resolution) else "N/A")

    st.divider()

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Risk Level Distribution")
        risk_counts = events_df["risk_level"].value_counts().reindex(["Low", "Medium", "High", "Critical"]).fillna(0)
        fig = px.bar(
            x=risk_counts.index, y=risk_counts.values,
            color=risk_counts.index,
            color_discrete_map=RISK_COLORS,
            labels={"x": "Risk Level", "y": "Number of Incidents"},
        )
        fig.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Incidents by Cause")
        cause_counts = events_df["event_cause"].value_counts().head(10)
        cause_labels = [CAUSE_LABELS.get(c, c) for c in cause_counts.index]
        fig = px.bar(
            x=cause_counts.values, y=cause_labels, orientation="h",
            labels={"x": "Number of Incidents", "y": ""},
            color_discrete_sequence=["#2E86AB"],
        )
        fig.update_layout(height=350, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    col_c, col_d = st.columns(2)

    with col_c:
        st.subheader("Planned vs Unplanned Events")
        type_counts = events_df["event_type"].value_counts()
        fig = px.pie(
            names=type_counts.index, values=type_counts.values,
            color_discrete_sequence=["#E63946", "#06A77D"],
            hole=0.45,
        )
        fig.update_layout(height=320)
        st.plotly_chart(fig, use_container_width=True)

    with col_d:
        st.subheader("Top 5 Most Fragile Corridors")
        bottom_tri = tri_df.sort_values("TRI").head(5)[["corridor", "TRI", "event_count"]]
        bottom_tri.columns = ["Corridor", "TRI Score", "Event Count"]
        st.dataframe(bottom_tri, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Incidents Requiring Road Closure")
    closure_pct = events_df["requires_road_closure"].mean() * 100
    st.progress(closure_pct / 100, text=f"{closure_pct:.1f}% of all incidents required a road closure")
