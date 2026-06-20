"""
TRAFICOP - AI Copilot for Bengaluru Traffic Operations
Predict. Respond. Divert.

Flipkart Gridlock 2.0 - Round 2
Theme: Event-Driven Congestion (Planned & Unplanned)

Run with: streamlit run app.py
"""
import streamlit as st

st.set_page_config(
    page_title="TRAFICOP | Bengaluru Traffic Command Center",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- Global CSS for a command-center look ----
st.markdown("""
<style>
    .main { background-color: #0E1117; }
    div[data-testid="stMetricValue"] { font-size: 28px; font-weight: 700; }
    .block-container { padding-top: 1.5rem; }
    .risk-critical { color: #E63946; font-weight: 700; }
    .risk-high { color: #F77F00; font-weight: 700; }
    .risk-medium { color: #F2C14E; font-weight: 700; }
    .risk-low { color: #06A77D; font-weight: 700; }
    h1, h2, h3 { font-family: 'Segoe UI', sans-serif; }
</style>
""", unsafe_allow_html=True)

from utils.core import load_corridor_tri, get_combined_events, init_live_incidents, clear_live_incidents
from utils.mappls_client import connection_status

init_live_incidents()

st.sidebar.title("🚦 TRAFICOP")
st.sidebar.caption("AI Copilot for Bengaluru Traffic Operations")
st.sidebar.markdown("**Predict. Respond. Divert.**")

_status = connection_status()
if _status in ("active_rest_key", "active_oauth"):
    st.sidebar.success("🟢 Mappls live map: Connected")
elif _status == "error":
    st.sidebar.warning("🟡 Mappls configured but unreachable — using fallback map")
else:
    st.sidebar.info("⚪ Mappls not configured — using OpenStreetMap fallback")

_live_count = len(st.session_state.get("live_incidents", []))
if _live_count > 0:
    st.sidebar.success(f"🔴 {_live_count} live simulated incident{'s' if _live_count != 1 else ''} active this session")
    if st.sidebar.button("Clear live incidents", use_container_width=True):
        clear_live_incidents()
        st.rerun()

st.sidebar.divider()

PAGES = [
    "Executive KPIs",
    "Bengaluru Command Map",
    "TRI Dashboard",
    "Analytics",
    "SHAP Explainability",
    "Incident Simulator",
    "Recommendations",
]

page = st.sidebar.radio("Navigate", PAGES, label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.caption("ASTraM Event Dataset | 8,173 Bengaluru traffic events")
st.sidebar.caption("Flipkart Gridlock 2.0 — Round 2")

# Load shared data once - historical dataset + any incidents simulated this session
events_df = get_combined_events()
tri_df = load_corridor_tri()

if page == "Executive KPIs":
    from pages_content import page_kpis
    page_kpis.render(events_df, tri_df)
elif page == "Bengaluru Command Map":
    from pages_content import page_map
    page_map.render(events_df, tri_df)
elif page == "TRI Dashboard":
    from pages_content import page_tri
    page_tri.render(events_df, tri_df)
elif page == "Analytics":
    from pages_content import page_analytics
    page_analytics.render(events_df, tri_df)
elif page == "SHAP Explainability":
    from pages_content import page_shap
    page_shap.render(events_df, tri_df)
elif page == "Incident Simulator":
    from pages_content import page_simulator
    page_simulator.render(events_df, tri_df)
elif page == "Recommendations":
    from pages_content import page_recommendations
    page_recommendations.render(events_df, tri_df)
