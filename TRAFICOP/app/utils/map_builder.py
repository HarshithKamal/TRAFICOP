"""
TRAFICOP - Map builder.
Builds the interactive Bengaluru Command Map with colored risk markers,
heatmap layer, TRI corridor layer, and event-type layer toggles.

Tile source: uses live Mappls (MapmyIndia) tiles when MAPPLS_REST_KEY is
configured in Streamlit secrets/.env; otherwise falls back automatically to
OpenStreetMap / CartoDB tiles so the app always renders a working map.
"""
import folium
from folium.plugins import HeatMap, MarkerCluster
import pandas as pd

from utils.core import RISK_COLORS, CAUSE_LABELS
from utils.mappls_client import get_tile_url_template, is_configured

BENGALURU_CENTER = [12.9716, 77.5946]
MAPPLS_ATTR = "&copy; Mappls (MapmyIndia)"


def build_command_map(events_df: pd.DataFrame, tri_df: pd.DataFrame, max_markers: int = 1500):
    """
    Build the full interactive command map with layer controls:
    - Base tiles: Mappls (live, if configured) or OSM/CartoDB fallback
    - Incident markers (color-coded by risk_level), clustered
    - Heatmap layer (incident density)
    - TRI layer (corridor circles sized/colored by resilience)
    """
    mappls_tiles = get_tile_url_template()

    if mappls_tiles:
        m = folium.Map(location=BENGALURU_CENTER, zoom_start=11, tiles=None)
        folium.TileLayer(tiles=mappls_tiles, attr=MAPPLS_ATTR, name="Mappls (live)", control=True).add_to(m)
    else:
        m = folium.Map(location=BENGALURU_CENTER, zoom_start=11, tiles="CartoDB positron")

    folium.TileLayer("OpenStreetMap", name="Street Map (fallback)").add_to(m)
    folium.TileLayer("CartoDB dark_matter", name="Command Center (Dark)").add_to(m)

    # ---- Layer 1: Historical incident markers, clustered for performance ----
    plot_df = events_df.dropna(subset=["latitude", "longitude"]).copy()
    if "source" not in plot_df.columns:
        plot_df["source"] = "historical"

    historical_df = plot_df[plot_df["source"] != "live"]
    live_df = plot_df[plot_df["source"] == "live"]

    if len(historical_df) > max_markers:
        historical_df = historical_df.sample(max_markers, random_state=42)

    marker_layer = MarkerCluster(name="Incidents (click for details)").add_to(m)

    for _, row in historical_df.iterrows():
        _add_incident_marker(marker_layer, row, pulsing=False)

    # ---- Layer 1b: Live simulated incidents - always visible, never clustered,
    # pulsing star icon so they're unmistakably distinct from historical data ----
    if len(live_df) > 0:
        live_layer = folium.FeatureGroup(name="🔴 Live Simulated Incidents", show=True)
        for _, row in live_df.iterrows():
            _add_incident_marker(live_layer, row, pulsing=True)
        live_layer.add_to(m)

    # ---- Layer 2: Heatmap ----
    heat_data = plot_df[["latitude", "longitude"]].values.tolist()
    HeatMap(heat_data, name="Incident Density Heatmap", radius=14, blur=18, show=False).add_to(m)

    # ---- Layer 3: TRI corridor layer (circle sized by event count, colored by TRI) ----
    tri_layer = folium.FeatureGroup(name="Corridor TRI Layer", show=False)
    corridor_centers = plot_df.groupby("corridor")[["latitude", "longitude"]].mean()
    for _, trow in tri_df.iterrows():
        corridor = trow["corridor"]
        if corridor not in corridor_centers.index:
            continue
        lat, lon = corridor_centers.loc[corridor]
        tri_val = trow["TRI"]
        tri_color = "#E63946" if tri_val < 50 else "#F77F00" if tri_val < 65 else "#06A77D"
        folium.Circle(
            location=[lat, lon],
            radius=600,
            color=tri_color,
            fill=True,
            fill_color=tri_color,
            fill_opacity=0.25,
            popup=f"<b>{corridor}</b><br>TRI: {tri_val}<br>Events: {int(trow['event_count'])}",
            tooltip=f"{corridor}: TRI {tri_val}",
        ).add_to(tri_layer)
    tri_layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


def _build_popup_html(row, color, cause_label, risk, is_live=False):
    live_badge = (
        '<div style="background:#E63946; color:white; font-size:11px; font-weight:700; '
        'padding:2px 8px; border-radius:10px; display:inline-block; margin-bottom:6px;">'
        '🔴 LIVE SIMULATED INCIDENT</div><br>'
    ) if is_live else ""
    return f"""
    <div style="font-family: Arial, sans-serif; font-size: 13px; min-width: 240px;">
        {live_badge}
        <h4 style="margin:0 0 6px 0; color:{color};">{cause_label}</h4>
        <table style="width:100%; border-collapse: collapse;">
            <tr><td><b>Event Type:</b></td><td>{row.get('event_type','-')}</td></tr>
            <tr><td><b>Corridor:</b></td><td>{row.get('corridor','-')}</td></tr>
            <tr><td><b>Priority:</b></td><td>{row.get('priority','-')}</td></tr>
            <tr><td><b>Risk Level:</b></td><td><b style="color:{color};">{risk}</b></td></tr>
            <tr><td><b>Impact Score:</b></td><td>{row.get('impact_score','-')}</td></tr>
            <tr><td><b>Resolution Time:</b></td><td>{_fmt_minutes(row.get('resolution_minutes'))}</td></tr>
            <tr><td><b>Officers Required:</b></td><td>{row.get('officers','-')}</td></tr>
            <tr><td><b>Barricades Required:</b></td><td>{row.get('barricades','-')}</td></tr>
            <tr><td><b>Tow Vehicle:</b></td><td>{row.get('tow_vehicle','-')}</td></tr>
            <tr><td><b>Escalation:</b></td><td>{row.get('escalation','-')}</td></tr>
            <tr><td><b>Diversion:</b></td><td>{row.get('suggested_diversions','-')}</td></tr>
        </table>
    </div>
    """


def _add_incident_marker(layer, row, pulsing=False):
    """Adds one incident marker to the given folium layer/cluster. Live (simulated)
    incidents render as a pulsing star DivIcon instead of a plain circle, so they're
    immediately recognizable as distinct from historical data on the map."""
    risk = row.get("risk_level", "Medium")
    color = RISK_COLORS.get(risk, "#808080")
    cause_label = CAUSE_LABELS.get(row.get("event_cause", ""), row.get("event_cause", "Unknown"))
    popup_html = _build_popup_html(row, color, cause_label, risk, is_live=pulsing)

    if pulsing:
        star_icon_html = f"""
        <div class="traficop-pulse-marker" style="position:relative; width:34px; height:34px;">
            <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
                        width:34px; height:34px; border-radius:50%; background:{color};
                        opacity:0.35; animation:traficop-pulse 1.6s ease-out infinite;"></div>
            <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
                        font-size:20px; line-height:1; filter:drop-shadow(0 0 2px rgba(0,0,0,0.6));">⭐</div>
        </div>
        <style>
        @keyframes traficop-pulse {{
            0%   {{ transform:translate(-50%,-50%) scale(0.6); opacity:0.55; }}
            70%  {{ transform:translate(-50%,-50%) scale(2.2); opacity:0; }}
            100% {{ transform:translate(-50%,-50%) scale(2.2); opacity:0; }}
        }}
        </style>
        """
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=folium.Popup(popup_html, max_width=320),
            tooltip=f"🔴 LIVE: {cause_label} - {risk}",
            icon=folium.DivIcon(html=star_icon_html, icon_size=(34, 34), icon_anchor=(17, 17)),
        ).add_to(layer)
    else:
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=7,
            popup=folium.Popup(popup_html, max_width=320),
            tooltip=f"{cause_label} - {risk}",
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            weight=2,
        ).add_to(layer)


def _fmt_minutes(val):
    if val is None or pd.isna(val):
        return "Unresolved / Active"
    val = float(val)
    if val < 60:
        return f"{val:.0f} min"
    hrs = val / 60
    if hrs < 24:
        return f"{hrs:.1f} hrs"
    days = hrs / 24
    return f"{days:.1f} days"


def build_simulator_map(lat, lon, end_lat, end_lon, risk_level, corridor):
    """Small focused map for the Incident Simulator page showing the simulated event location."""
    mappls_tiles = get_tile_url_template()
    if mappls_tiles:
        m = folium.Map(location=[lat, lon], zoom_start=14, tiles=None)
        folium.TileLayer(tiles=mappls_tiles, attr=MAPPLS_ATTR, name="Mappls (live)").add_to(m)
    else:
        m = folium.Map(location=[lat, lon], zoom_start=14, tiles="CartoDB positron")
    color = RISK_COLORS.get(risk_level, "#808080")
    folium.Marker(
        location=[lat, lon],
        popup=f"Simulated Incident<br>Corridor: {corridor}<br>Risk: {risk_level}",
        icon=folium.Icon(color="red" if risk_level in ["Critical", "High"] else "orange", icon="exclamation-triangle", prefix="fa"),
    ).add_to(m)
    if end_lat and end_lon:
        folium.PolyLine([[lat, lon], [end_lat, end_lon]], color=color, weight=5, opacity=0.8).add_to(m)
    folium.Circle(location=[lat, lon], radius=400, color=color, fill=True, fill_opacity=0.15).add_to(m)
    return m
