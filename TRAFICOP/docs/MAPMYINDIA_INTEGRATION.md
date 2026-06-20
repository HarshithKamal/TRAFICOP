# Mappls Integration Guide

This document covers the **live Mappls (MapmyIndia) integration** that powers TRAFICOP's map tiles and Diversion Engine (Module 7). The integration code is already in `app/utils/mappls_client.py` and `app/utils/core.py` — it activates automatically the moment you add your Mappls credentials, with zero code changes required. Until then, the app runs on its built-in OpenStreetMap + corridor-logic fallback, so you always have a working demo regardless of API approval timing.

---

## A. Account Creation

1. Go to **https://outpost.mappls.com/console/** (the Mappls API Console — also linked from `about.mappls.com/api/`).
2. Click **Sign Up**, register with your email. Verify the email.
3. Once logged in, click **Create a new Project**. Name it `TRAFICOP`.
4. **Approval/activation is typically immediate** for the free developer tier — no business KYC required for development/testing credits, no credit card needed.

## B. API Key Generation

1. Inside your project, go to **Credentials** (or **API Keys**).
2. You'll find:
   - **Client ID** and **Client Secret** — used for OAuth2 token generation (covers most modern APIs)
   - **REST API Key** — a simpler static key, used for tile URLs and some v1-style endpoints
3. Copy whichever set you have. **TRAFICOP's code accepts either** — you only need to set the ones your console gave you.
4. Map these directly into the credential names TRAFICOP already expects (see Secrets Management in `docs/DEPLOYMENT_GUIDE.md`):
   - `MAPPLS_CLIENT_ID`
   - `MAPPLS_CLIENT_SECRET`
   - `MAPPLS_REST_KEY`

## C. Required APIs for TRAFICOP

| API | Used for |
|---|---|
| **Routing API** | Primary route + alternate route calculation between two points (the diversion engine's main call) |
| **Places API** | Resolving corridor names to lat/long if you need geocoding beyond what's in the dataset |
| **Traffic API** (if available on your plan) | Live traffic layer overlay on the map |
| **Maps SDK / Static Maps API** | Rendering the actual map tiles if you replace Folium's OpenStreetMap tiles with MapmyIndia tiles |

## D. Pricing Notes

- MapmyIndia typically offers a **free tier with a limited number of monthly API calls** (check current limits in your console — these change, so don't hardcode an assumption into your pitch deck).
- Routing API calls are usually metered separately from Maps/tile rendering calls.
- For a hackathon demo, the free tier is almost always sufficient — you're not serving production traffic.
- **Do not** put pricing numbers in your pitch deck without checking the current console — pricing pages change without notice, and quoting a stale price to judges undermines credibility.

## E. Authentication

REST API Key style (most common):

```
GET https://apis.mapmyindia.com/advancedmaps/v1/{your_rest_key}/route_adv/driving/{start_lng},{start_lat};{end_lng},{end_lat}?alternatives=true
```

The key is embedded directly in the URL path for v1 APIs — there is no separate Authorization header for this style.

OAuth style (for newer APIs):

```python
import requests

def get_oauth_token(client_id, client_secret):
    response = requests.post(
        "https://outpost.mapmyindia.com/api/security/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    return response.json()["access_token"]
```

## F. Integration Code (already implemented)

The full client is in `app/utils/mappls_client.py`. Key pieces:

```python
TOKEN_URL = "https://outpost.mappls.com/api/security/oauth/token"
DISTANCE_URL = "https://apis.mappls.com/advancedmaps/v2/{key}/distance"
TILE_URL_TEMPLATE = "https://apis.mappls.com/advancedmaps/v1/{key}/map_tile/{{z}}/{{x}}/{{y}}.png"

def get_distance_eta(source_lat, source_lng, target_lat, target_lng, profile="driving"):
    """
    Calls Mappls Distance/ETA API for a single source -> target pair.
    Returns {'distance_m': float, 'duration_s': float} or None on failure
    (including when not configured, so callers can fall back to corridor logic).
    """
    # full implementation in app/utils/mappls_client.py
```

You don't need to write or copy any code — this is already wired into `app/utils/core.py`'s `get_diversion_routes_live()` and `app/utils/map_builder.py`'s tile layer selection. Adding your credentials to Streamlit secrets is the only step required.

## G. Route Visualization

To draw a MapmyIndia-returned polyline on the Folium map (you can mix MapmyIndia routing with Folium rendering — they're not mutually exclusive):

```python
import polyline as polyline_lib  # pip install polyline
import folium

def add_route_to_map(folium_map, encoded_polyline, color="#2E86AB"):
    coords = polyline_lib.decode(encoded_polyline)  # returns list of (lat, lng)
    folium.PolyLine(coords, color=color, weight=5, opacity=0.8).add_to(folium_map)
    return folium_map
```

If you fully switch to MapmyIndia's own Maps SDK (JS-based) instead of Folium, you'd embed it via an HTML component in Streamlit using `streamlit.components.v1.html()` and the MapmyIndia JS SDK `<script>` tag — this requires more involved iframe/postMessage handling, which is the main integration cost mentioned in the README.

## H. Alternative Route Suggestions

The `alternatives=true` parameter in the Routing API call above already requests alternate routes. In TRAFICOP, you'd rank these alternates by a combination of:
- Duration (lower is better)
- Whether the alternate passes through another corridor currently flagged High/Critical risk (avoid stacking diversions onto already-congested corridors — cross-reference against the live `risk_level` column in `processed_events.csv`)

## I. Traffic Layer Integration

If your MapmyIndia plan includes a live traffic layer, it's typically delivered as an XYZ tile layer you can add directly as a Folium TileLayer:

```python
folium.TileLayer(
    tiles=f"https://traffic.mapmyindia.com/tiles/{{z}}/{{x}}/{{y}}.png?key={MAPMYINDIA_REST_KEY}",
    attr="MapmyIndia Traffic",
    name="Live Traffic",
    overlay=True,
).add_to(folium_map)
```

**Note:** confirm the exact tile URL pattern and product name in your MapmyIndia console — traffic-layer products and endpoint paths vary by plan and have changed across MapmyIndia's product versions, so do not assume this exact URL works without checking your account's API documentation page first.

## J. Fallback Folium Implementation (already wired in — this is the safety net, not a placeholder)

This integration is **already live in the codebase**, not just documented. `app/utils/mappls_client.py` implements exactly the OAuth token flow and tile/distance calls described in sections E–H above, using the real, current Mappls endpoints:

- Token: `POST https://outpost.mappls.com/api/security/oauth/token`
- Tiles: `https://apis.mappls.com/advancedmaps/v1/{key}/map_tile/{z}/{x}/{y}.png`
- Distance/ETA: `https://apis.mappls.com/advancedmaps/v2/distance` (OAuth) or `.../v1/{key}/distance_matrix/...` (REST key)

`app/utils/core.py`'s static `CORRIDOR_DIVERSIONS` table is the **fallback layer**, not a separate implementation you'd swap in later:

```python
CORRIDOR_DIVERSIONS = {
    'Mysore Road': ['Magadi Road', 'Old Madras Road via Ring Road'],
    'Hosur Road': ['Bannerghata Road', 'ORR East 1'],
    # ... full mapping in utils/core.py
}

def get_diversion_routes(corridor):
    return CORRIDOR_DIVERSIONS.get(corridor, ['No predefined diversion - manual assessment required'])
```

`get_diversion_routes_live()` in `core.py` calls this static table to get the *candidate* corridors, then — only if Mappls credentials are configured — calls the live Distance API to rank those candidates by real driving ETA. If the live call fails for any reason (no credits, network blip, invalid key), it silently returns the static order instead. **The map, the diversion engine, and the sidebar status indicator all auto-detect credential presence at runtime** — there is no manual toggle or separate "demo mode" to switch.


*"TRAFICOP's map and diversion engine run on live Mappls APIs as the primary path, with the same corridor logic acting as an automatic, zero-downtime fallback if a live call fails. We built it this way because real traffic-command software can't go dark because a third-party API hiccupped during a live incident."* This is true today, in the code, not aspirational.
