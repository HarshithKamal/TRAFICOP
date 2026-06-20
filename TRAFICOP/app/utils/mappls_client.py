"""
TRAFICOP - Mappls (MapmyIndia) API client.

Handles:
- OAuth2 token generation/caching from Client ID + Client Secret
- Distance/ETA calls (Mappls Distance API v2)
- Raster tile URL construction for the command map
- Graceful "not configured" detection so the rest of the app can fall back
  to Folium + OpenStreetMap when no Mappls credentials are present.

Credentials are read from Streamlit secrets first, then environment variables,
so this works both on Streamlit Cloud (secrets.toml) and locally (.env / shell env).

Required secrets/env vars (set only the ones you have):
    MAPPLS_CLIENT_ID
    MAPPLS_CLIENT_SECRET
    MAPPLS_REST_KEY        (optional - used for tile URLs and simpler v1 calls)
"""
import time
import requests
import streamlit as st

TOKEN_URL = "https://outpost.mappls.com/api/security/oauth/token"
DISTANCE_URL = "https://apis.mappls.com/advancedmaps/v2/{key}/distance"
TILE_URL_TEMPLATE = "https://apis.mappls.com/advancedmaps/v1/{key}/map_tile/{{z}}/{{x}}/{{y}}.png"


def _get_secret(name):
    """Read a credential from Streamlit secrets first, falling back to env vars."""
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    import os
    return os.environ.get(name, "")


def get_credentials():
    return {
        "client_id": _get_secret("MAPPLS_CLIENT_ID"),
        "client_secret": _get_secret("MAPPLS_CLIENT_SECRET"),
        "rest_key": _get_secret("MAPPLS_REST_KEY"),
    }


def is_configured():
    """True only if enough credentials are present to make real Mappls calls."""
    creds = get_credentials()
    has_oauth = bool(creds["client_id"] and creds["client_secret"])
    has_rest_key = bool(creds["rest_key"])
    return has_oauth or has_rest_key


@st.cache_resource(ttl=82800)  # cache just under the 24h token lifetime
def _get_access_token(client_id: str, client_secret: str):
    """
    Exchanges Client ID + Client Secret for a bearer token via Mappls OAuth2.
    Cached for ~23 hours (tokens are valid 24h by default) so we don't
    re-authenticate on every page load.
    """
    if not client_id or not client_secret:
        return None
    try:
        resp = requests.post(
            TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "access_token": data["access_token"],
            "token_type": data.get("token_type", "bearer"),
            "fetched_at": time.time(),
        }
    except Exception as e:
        try:
            st.session_state["_mappls_token_error"] = str(e)
        except Exception:
            pass  # session_state unavailable outside a running Streamlit script - safe to skip
        return None


def get_auth_header():
    """Returns a ready-to-use Authorization header dict, or None if unavailable."""
    creds = get_credentials()
    if not (creds["client_id"] and creds["client_secret"]):
        return None
    token = _get_access_token(creds["client_id"], creds["client_secret"])
    if not token:
        return None
    return {"Authorization": f"{token['token_type']} {token['access_token']}"}


def get_tile_url_template():
    """
    Returns an {z}/{x}/{y} tile URL template for Folium's TileLayer, using the
    Mappls REST key. Returns None if no REST key is configured (caller should
    fall back to OpenStreetMap tiles in that case).
    """
    creds = get_credentials()
    if not creds["rest_key"]:
        return None
    return TILE_URL_TEMPLATE.format(key=creds["rest_key"])


def get_distance_eta(source_lat, source_lng, target_lat, target_lng, profile="driving"):
    """
    Calls Mappls Distance/ETA API for a single source -> target pair.
    Returns {'distance_m': float, 'duration_s': float} or None on failure
    (including when not configured, so callers can fall back to corridor logic).
    """
    creds = get_credentials()
    headers = get_auth_header()

    if creds["rest_key"]:
        # Simpler v1-style key-in-path call when only a REST key is available
        url = f"https://apis.mappls.com/advancedmaps/v1/{creds['rest_key']}/distance_matrix/{profile}/{source_lng},{source_lat};{target_lng},{target_lat}"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", {}).get("distances")
            durations = data.get("results", {}).get("durations")
            if results and durations:
                return {"distance_m": results[0][1], "duration_s": durations[0][1]}
        except Exception:
            pass

    if headers:
        params = {
            "source": f"{source_lng},{source_lat}",
            "target": f"{target_lng},{target_lat}",
            "profile": profile,
        }
        try:
            resp = requests.get(
                "https://apis.mappls.com/advancedmaps/v2/distance",
                params=params, headers=headers, timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            row = data.get("results", [{}])[0]
            return {"distance_m": row.get("distance"), "duration_s": row.get("duration")}
        except Exception:
            pass

    return None


def connection_status():
    """
    Returns a short human-readable status string for display in the sidebar/UI,
    so the team can see at a glance whether the live Mappls map is active.
    """
    if not is_configured():
        return "not_configured"
    creds = get_credentials()
    if creds["rest_key"]:
        return "active_rest_key"
    header = get_auth_header()
    if header:
        return "active_oauth"
    return "error"
