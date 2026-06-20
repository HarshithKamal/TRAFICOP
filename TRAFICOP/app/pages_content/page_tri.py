import streamlit as st
import pandas as pd
import plotly.express as px


def render(events_df: pd.DataFrame, tri_df: pd.DataFrame):
    st.title("🛡️ Traffic Resilience Index (TRI) Dashboard")
    st.caption("Corridor-level resilience scoring — higher TRI = more resilient, lower TRI = more fragile")

    with st.expander("ℹ️ What is TRI?", expanded=False):
        st.markdown("""
**TRI** (0–100) measures how well a corridor absorbs traffic disruption, combining:
- **Event frequency** (30%) — how often incidents occur on this corridor
- **Resolution time** (30%) — how long incidents typically take to clear
- **High-priority ratio** (25%) — fraction of incidents flagged High priority
- **Average impact score** (15%) — average severity of incidents on this corridor

```
TRI = 100 - (freq_norm*30 + res_norm*30 + hp_ratio*25 + impact_norm*15)
```

A **low TRI** corridor needs proactive attention: more patrol presence, faster response protocols, or infrastructure review.
        """)

    sorted_tri = tri_df.sort_values("TRI")

    col1, col2, col3 = st.columns(3)
    col1.metric("Most Fragile Corridor", sorted_tri.iloc[0]["corridor"], f"TRI {sorted_tri.iloc[0]['TRI']:.1f}")
    col2.metric("Most Resilient Corridor", sorted_tri.iloc[-1]["corridor"], f"TRI {sorted_tri.iloc[-1]['TRI']:.1f}")
    col3.metric("Network Average TRI", f"{tri_df['TRI'].mean():.1f}")

    st.divider()

    st.subheader("TRI by Corridor")
    plot_data = sorted_tri.copy()
    plot_data["color_band"] = plot_data["TRI"].apply(lambda t: "Fragile (<50)" if t < 50 else "Watch (50-65)" if t < 65 else "Resilient (65+)")
    fig = px.bar(
        plot_data, x="TRI", y="corridor", orientation="h",
        color="color_band",
        color_discrete_map={"Fragile (<50)": "#E63946", "Watch (50-65)": "#F77F00", "Resilient (65+)": "#06A77D"},
        labels={"TRI": "Traffic Resilience Index", "corridor": "Corridor"},
        height=600,
    )
    fig.update_layout(yaxis=dict(categoryorder="total ascending"))
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Full Corridor Resilience Table")
    display_cols = ["corridor", "event_count", "high_priority_ratio", "median_resolution_minutes", "avg_impact", "TRI"]
    display_df = sorted_tri[display_cols].copy()
    display_df.columns = ["Corridor", "Event Count", "High Priority Ratio", "Median Resolution (min)", "Avg Impact Score", "TRI"]
    display_df["High Priority Ratio"] = (display_df["High Priority Ratio"] * 100).round(1).astype(str) + "%"
    display_df["Median Resolution (min)"] = display_df["Median Resolution (min)"].round(1)
    display_df["Avg Impact Score"] = display_df["Avg Impact Score"].round(1)
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("⚠️ Corridors Requiring Priority Attention")
    fragile = sorted_tri[sorted_tri["TRI"] < 65].head(5)
    for _, row in fragile.iterrows():
        st.warning(
            f"**{row['corridor']}** — TRI {row['TRI']:.1f} | "
            f"{int(row['event_count'])} historical events | "
            f"{row['high_priority_ratio']*100:.0f}% high priority | "
            f"median resolution {row['median_resolution_minutes']:.0f} min"
        )
