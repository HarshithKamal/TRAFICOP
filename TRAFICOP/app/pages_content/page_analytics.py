import streamlit as st
import pandas as pd
import plotly.express as px

from utils.core import CAUSE_LABELS


def render(events_df: pd.DataFrame, tri_df: pd.DataFrame):
    st.title("📈 Analytics")
    st.caption("Deep-dive patterns across time, geography, and incident type")

    tab1, tab2, tab3 = st.tabs(["Time Patterns", "Resolution Time Analysis", "Corridor Deep-Dive"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Incidents by Hour of Day")
            hourly = events_df["hour"].value_counts().sort_index()
            fig = px.bar(x=hourly.index, y=hourly.values, labels={"x": "Hour", "y": "Incidents"},
                         color_discrete_sequence=["#2E86AB"])
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Incidents by Time Period")
            period_order = ["morning_peak", "midday", "evening_peak", "night", "late_night"]
            period_counts = events_df["time_period"].value_counts().reindex(period_order).fillna(0)
            fig = px.bar(
                x=[p.replace("_", " ").title() for p in period_counts.index],
                y=period_counts.values,
                labels={"x": "Time Period", "y": "Incidents"},
                color_discrete_sequence=["#6A4C93"],
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Weekday vs Weekend")
        wk = events_df["is_weekend"].map({0: "Weekday", 1: "Weekend"}).value_counts()
        fig = px.pie(names=wk.index, values=wk.values, hole=0.45,
                     color_discrete_sequence=["#2E86AB", "#F77F00"])
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Resolution Time by Event Cause (median, minutes)")
        clean = events_df[(events_df["resolution_minutes"] > 0) & (events_df["resolution_minutes"] <= 10080)]
        med_by_cause = clean.groupby("event_cause")["resolution_minutes"].median().sort_values()
        labels = [CAUSE_LABELS.get(c, c) for c in med_by_cause.index]
        fig = px.bar(x=med_by_cause.values, y=labels, orientation="h",
                     labels={"x": "Median Resolution Time (min)", "y": ""},
                     color_discrete_sequence=["#06A77D"])
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Resolution Time Distribution")
        fig2 = px.histogram(
            clean[clean["resolution_minutes"] <= 1440], x="resolution_minutes", nbins=50,
            labels={"resolution_minutes": "Resolution Time (minutes, capped at 24h for readability)"},
            color_discrete_sequence=["#2E86AB"],
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(f"Showing {(clean['resolution_minutes'] <= 1440).sum():,} of {len(clean):,} resolved incidents (≤24 hours). "
                   f"A smaller set of incidents — mainly pot holes, water logging, and construction — legitimately take longer to fully resolve.")

    with tab3:
        st.subheader("Event Count by Corridor")
        corridor_counts = events_df["corridor"].value_counts().head(15)
        fig = px.bar(x=corridor_counts.values, y=corridor_counts.index, orientation="h",
                     labels={"x": "Incidents", "y": ""}, color_discrete_sequence=["#F77F00"])
        fig.update_layout(height=500, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Impact Score Heatmap: Corridor x Event Cause")
        top_corridors = events_df["corridor"].value_counts().head(10).index
        top_causes = events_df["event_cause"].value_counts().head(8).index
        pivot = events_df[
            events_df["corridor"].isin(top_corridors) & events_df["event_cause"].isin(top_causes)
        ].pivot_table(values="impact_score", index="corridor", columns="event_cause", aggfunc="mean")
        pivot.columns = [CAUSE_LABELS.get(c, c) for c in pivot.columns]
        fig3 = px.imshow(pivot, color_continuous_scale="OrRd", aspect="auto",
                          labels=dict(color="Avg Impact Score"))
        fig3.update_layout(height=450)
        st.plotly_chart(fig3, use_container_width=True)
