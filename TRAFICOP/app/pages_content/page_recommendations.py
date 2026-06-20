import streamlit as st
import pandas as pd
import plotly.express as px

from utils.core import CAUSE_LABELS


def render(events_df: pd.DataFrame, tri_df: pd.DataFrame):
    st.title("🚓 Recommendations Overview")
    st.caption("Aggregate resource demand across all incidents — for shift planning and resource allocation")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Officers Recommended", f"{events_df['officers'].sum():,.0f}")
    col2.metric("Total Barricades Recommended", f"{events_df['barricades'].sum():,.0f}")
    col3.metric("Incidents Needing Tow Vehicle", f"{(events_df['tow_vehicle']=='Yes').sum():,}")
    col4.metric("Incidents Needing Escalation", f"{(events_df['escalation']!='No').sum():,}")

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Officer Demand by Risk Level")
        officer_by_risk = events_df.groupby("risk_level")["officers"].sum().reindex(["Low", "Medium", "High", "Critical"]).fillna(0)
        fig = px.bar(x=officer_by_risk.index, y=officer_by_risk.values,
                     color=officer_by_risk.index,
                     color_discrete_map={"Critical": "#E63946", "High": "#F77F00", "Medium": "#F2C14E", "Low": "#06A77D"},
                     labels={"x": "Risk Level", "y": "Total Officers Recommended"})
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Tow Vehicle Demand by Cause")
        tow_df = events_df[events_df["tow_vehicle"] == "Yes"]
        tow_counts = tow_df["event_cause"].value_counts()
        labels = [CAUSE_LABELS.get(c, c) for c in tow_counts.index]
        fig2 = px.pie(names=labels, values=tow_counts.values, hole=0.4)
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("Corridors with Highest Resource Demand")
    corridor_demand = events_df.groupby("corridor").agg(
        total_officers=("officers", "sum"),
        total_barricades=("barricades", "sum"),
        incident_count=("id", "count"),
    ).sort_values("total_officers", ascending=False).head(10).reset_index()
    corridor_demand.columns = ["Corridor", "Total Officers", "Total Barricades", "Incident Count"]
    st.dataframe(corridor_demand, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("🚨 Incidents Currently Requiring Escalation")
    escalated = events_df[(events_df["escalation"] != "No") & (events_df["status"] == "active")]
    if len(escalated) == 0:
        st.success("No active incidents currently require escalation.")
    else:
        show_cols = ["event_cause", "corridor", "priority", "risk_level", "escalation", "officers", "barricades"]
        display = escalated[show_cols].copy()
        display["event_cause"] = display["event_cause"].map(lambda c: CAUSE_LABELS.get(c, c))
        display.columns = ["Event Cause", "Corridor", "Priority", "Risk Level", "Escalation", "Officers", "Barricades"]
        st.dataframe(display, use_container_width=True, hide_index=True)
