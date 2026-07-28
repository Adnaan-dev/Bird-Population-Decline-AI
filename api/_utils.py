"""
Shared helpers for the Bird Population Decline AI serverless API.

This module is imported by the individual endpoints in /api. It contains:
  - Sentinel Hub OAuth + tile fetching (parsed with tifffile, no GDAL)
  - NDVI / NDWI / NDBI computation
  - RGB composite generation
  - Deterministic land-cover classification from spectral indices
  - Habitat-health / bird-decline-risk scoring
  - OpenWeather lookup
  - matplotlib-colormap -> base64 PNG encoding (for the frontend)

Design goal: keep everything lightweight so the function bundle stays well
under Vercel's Python size limit (no torch / torchvision / rasterio).
"""

import io
import os
import base64
import json
import time
from collections import OrderedDict, Counter
from datetime import datetime, timedelta, timezone

import numpy as np
import requests
import tifffile

import matplotlib
# On Vercel the filesystem is read-only except /tmp; point matplotlib's cache
# there so importing it never fails at cold start. Local/CI is unaffected.
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
matplotlib.use("Agg")
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from PIL import Image


# ----------------------------------------------------------------------------
# Configuration (read from environment; sensible fallbacks for local demo)
# ----------------------------------------------------------------------------
def _env(name, default=""):
    val = os.environ.get(name)
    return val if val not in (None, "") else default


MAPBOX_ACCESS_TOKEN = _env("MAPBOX_ACCESS_TOKEN")
OPENWEATHER_API_KEY = _env("OPENWEATHER_API_KEY")
SENTINEL_CLIENT_ID = _env("SENTINEL_CLIENT_ID")
SENTINEL_CLIENT_SECRET = _env("SENTINEL_CLIENT_SECRET")

# Band order requested from Sentinel-2 L2A.
#   0: B02 (Blue)  1: B03 (Green)  2: B04 (Red)  3: B08 (NIR)  4: B11 (SWIR1)  5: B12 (SWIR2)
BANDS = ["B02", "B03", "B04", "B08", "B11", "B12"]

EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B02","B03","B04","B08","B11","B12"], units: "REFLECTANCE" }],
    output: { bands: 6, sampleType: "FLOAT32" }
  };
}
function evaluatePixel(sample) {
  return [sample.B02, sample.B03, sample.B04, sample.B08, sample.B11, sample.B12];
}
"""

# Endpoints default to the Copernicus Data Space Ecosystem (CDSE), which is
# where free Sentinel Hub access now lives. Override via env vars to target the
# legacy/commercial services.sentinel-hub.com deployment if you have paid creds.
_SENTINEL_TOKEN_URL = _env(
    "SENTINEL_TOKEN_URL",
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
)
_SENTINEL_PROCESS_URL = _env(
    "SENTINEL_PROCESS_URL",
    "https://sh.dataspace.copernicus.eu/api/v1/process",
)
# STAC catalog endpoint (for scene metadata: acquisition date + cloud cover).
_SENTINEL_CATALOG_URL = _env(
    "SENTINEL_CATALOG_URL",
    _SENTINEL_PROCESS_URL.replace("/process", "/catalog/1.0.0/search"),
)


# ----------------------------------------------------------------------------
# Optional error monitoring (Sentry) — no-op unless SENTRY_DSN is set and the
# sentry-sdk package is installed. Never breaks the app if unavailable.
# ----------------------------------------------------------------------------
def _init_sentry():
    dsn = _env("SENTRY_DSN")
    if not dsn:
        return
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=dsn, traces_sample_rate=0.0)
    except Exception:  # noqa: BLE001
        pass


_init_sentry()

# Simple in-process token cache (persists for the life of a warm function).
_token_cache = {"token": None, "expires_at": 0.0}


class ApiError(Exception):
    """Raised for expected, user-facing API failures."""

    def __init__(self, message, status=500):
        super().__init__(message)
        self.message = message
        self.status = status


# ----------------------------------------------------------------------------
# Sentinel Hub
# ----------------------------------------------------------------------------
def get_sentinel_token():
    """Return a cached OAuth token, refreshing when needed."""
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    if not SENTINEL_CLIENT_ID or not SENTINEL_CLIENT_SECRET:
        raise ApiError(
            "Sentinel Hub credentials are not configured on the server "
            "(SENTINEL_CLIENT_ID / SENTINEL_CLIENT_SECRET).",
            status=500,
        )

    payload = {
        "client_id": SENTINEL_CLIENT_ID,
        "client_secret": SENTINEL_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }
    last_err = ""
    attempts = 3
    for attempt in range(attempts):
        try:
            r = requests.post(_SENTINEL_TOKEN_URL, data=payload, timeout=20)
            if r.status_code == 200:
                data = r.json()
                break
            last_err = f"{r.status_code}: {r.text[:200]}".strip()
            if r.status_code in (401, 403):
                raise ApiError(
                    "Sentinel Hub authentication failed. Check that SENTINEL_CLIENT_ID / "
                    "SENTINEL_CLIENT_SECRET are valid CDSE credentials.",
                    status=502,
                )
        except requests.RequestException as exc:
            last_err = f"network error: {exc}"
        if attempt < attempts - 1:
            time.sleep(1.0 * (attempt + 1))
    else:
        raise ApiError(f"Failed to obtain a Sentinel Hub token ({last_err}).", status=502)

    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + float(data.get("expires_in", 3600))
    return _token_cache["token"]


def fetch_sentinel_tile(lat, lon, token, dt=None, bbox_size=0.01, size=256, bbox=None):
    """
    Fetch a Sentinel-2 L2A tile around (lat, lon) and return a float32 array
    of shape (6, H, W) in band order [B02, B03, B04, B08, B11, B12].

    dt   : optional "YYYY-MM-DD" string to restrict to a single day.
    bbox : optional explicit [west, south, east, north] (for area analysis);
           when given it overrides the point + bbox_size box.
    """
    if bbox is None:
        bbox = [lon - bbox_size, lat - bbox_size, lon + bbox_size, lat + bbox_size]

    data_filter = {"maxCloudCoverage": 40}
    if dt is not None:
        data_filter["timeRange"] = {
            "from": f"{dt}T00:00:00Z",
            "to": f"{dt}T23:59:59Z",
        }

    payload = {
        "input": {
            "bounds": {
                "bbox": bbox,
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
            },
            "data": [{"type": "sentinel-2-l2a", "dataFilter": data_filter}],
        },
        "evalscript": EVALSCRIPT,
        "output": {
            "width": size,
            "height": size,
            "responses": [
                {"identifier": "default", "format": {"type": "image/tiff"}}
            ],
        },
    }

    headers = {"Authorization": f"Bearer {token}"}

    # Sentinel Hub occasionally returns transient 5xx / rate-limit responses.
    # Retry a few times with backoff before surfacing a user-facing error.
    transient = {429, 500, 502, 503, 504}
    last_err = ""
    attempts = 3
    for attempt in range(attempts):
        try:
            r = requests.post(_SENTINEL_PROCESS_URL, json=payload, headers=headers, timeout=60)
        except requests.RequestException as exc:
            last_err = f"network error: {exc}"
            if attempt < attempts - 1:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise ApiError(
                "Could not reach Sentinel Hub. Please check your connection and try again.",
                status=502,
            )

        if r.status_code == 200:
            break

        last_err = f"{r.status_code}: {r.text[:200]}".strip()
        if r.status_code in transient and attempt < attempts - 1:
            time.sleep(1.0 * (attempt + 1))
            continue
        if r.status_code in (401, 403):
            raise ApiError(
                "Sentinel Hub rejected the request (auth). Verify SENTINEL_CLIENT_ID / "
                "SENTINEL_CLIENT_SECRET are valid CDSE credentials.",
                status=502,
            )
        raise ApiError(
            f"Sentinel Hub could not return imagery for this location "
            f"(error {r.status_code}). Try a nearby point or a clearer date.",
            status=502,
        )
    else:  # pragma: no cover - loop always breaks or raises
        raise ApiError(f"Sentinel Hub request failed after retries ({last_err}).", status=502)

    # Empty body guard (no imagery matched the filters).
    if not r.content:
        raise ApiError(
            "No usable Sentinel-2 imagery was found for this location "
            "(likely cloud cover or a data gap). Try a nearby point.",
            status=502,
        )

    # Parse the multiband float32 GeoTIFF with tifffile (pure Python, no GDAL).
    try:
        arr = tifffile.imread(io.BytesIO(r.content)).astype(np.float32)
    except Exception as exc:  # noqa: BLE001
        raise ApiError(
            "Received an unreadable imagery response from Sentinel Hub. "
            "Please try again in a moment.",
            status=502,
        )
    return _to_chw(arr, nbands=len(BANDS))


def _to_chw(arr, nbands):
    """Normalise a tifffile array to channel-first (C, H, W)."""
    if arr.ndim == 2:  # single band
        arr = arr[np.newaxis, ...]
    elif arr.ndim == 3:
        # tifffile usually returns (H, W, C); Sentinel may return (C, H, W).
        if arr.shape[-1] == nbands and arr.shape[0] != nbands:
            arr = np.transpose(arr, (2, 0, 1))  # (H,W,C) -> (C,H,W)
        elif arr.shape[0] == nbands:
            pass  # already (C, H, W)
        elif arr.shape[-1] == nbands:
            arr = np.transpose(arr, (2, 0, 1))
    else:
        raise ApiError("Unexpected satellite tile shape from Sentinel Hub.", status=502)
    return arr


# ----------------------------------------------------------------------------
# Spectral indices & derived products
# ----------------------------------------------------------------------------
def compute_indices(tile):
    """Return (ndvi, ndwi, ndbi) from a (5+, H, W) tile. Kept for back-compat."""
    blue, green, red, nir, swir = tile[0], tile[1], tile[2], tile[3], tile[4]
    eps = 1e-6
    ndvi = (nir - red) / (nir + red + eps)
    ndwi = (green - nir) / (green + nir + eps)
    ndbi = (swir - nir) / (swir + nir + eps)
    return ndvi, ndwi, ndbi


def compute_all_indices(tile):
    """
    Return a dict of spectral indices from a (5+, H, W) tile.
    Robust to tiles without B12 (SWIR2): falls back to SWIR1 for NBR.

    NDVI (veg) · NDWI (water) · NDBI (built-up) · EVI · SAVI ·
    NDMI (moisture) · NBR (burn).
    """
    blue, green, red, nir, swir = tile[0], tile[1], tile[2], tile[3], tile[4]
    swir2 = tile[5] if tile.shape[0] > 5 else swir
    eps = 1e-6
    L = 0.5
    ndvi = (nir - red) / (nir + red + eps)
    ndwi = (green - nir) / (green + nir + eps)
    ndbi = (swir - nir) / (swir + nir + eps)
    savi = ((nir - red) / (nir + red + L + eps)) * (1.0 + L)
    evi = np.clip(2.5 * (nir - red) / (nir + 6.0 * red - 7.5 * blue + 1.0 + eps), -1.0, 1.0)
    ndmi = (nir - swir) / (nir + swir + eps)
    nbr = (nir - swir2) / (nir + swir2 + eps)
    return {"ndvi": ndvi, "ndwi": ndwi, "ndbi": ndbi,
            "savi": savi, "evi": evi, "ndmi": ndmi, "nbr": nbr}


def make_rgb(tile):
    """True-colour RGB composite (H, W, 3) in 0..1 from a (5, H, W) tile."""
    blue, green, red = tile[0], tile[1], tile[2]
    rgb = np.stack([red, green, blue], axis=-1)
    lo, hi = np.nanpercentile(rgb, 2), np.nanpercentile(rgb, 98)
    rgb = np.clip((rgb - lo) / (hi - lo + 1e-6), 0, 1)
    return rgb


def classify_landcover(ndvi_mean, ndwi_mean, ndbi_mean):
    """
    Deterministic land-cover label derived from the spectral indices.
    Replaces the previous randomly-initialised ResNet head (which produced
    meaningless labels) with rules grounded in remote-sensing conventions.
    """
    if ndwi_mean > 0.2:
        return "Water / Wetland"
    if ndbi_mean > 0.0 and ndvi_mean < 0.3:
        return "Urban / Built-up"
    if ndvi_mean >= 0.6:
        return "Dense Forest / Vegetation"
    if ndvi_mean >= 0.3:
        return "Moderate Vegetation / Cropland"
    return "Barren / Sparse Vegetation"


def analyze_tile(tile):
    """Run the full analysis pipeline on a (5+, H, W) tile."""
    idx = compute_all_indices(tile)
    rgb = make_rgb(tile)

    def m(a):
        return float(np.nanmean(a))

    ndvi_mean = m(idx["ndvi"])
    ndwi_mean = m(idx["ndwi"])
    ndbi_mean = m(idx["ndbi"])

    # Habitat health 0..100 from mean NDVI (same heuristic as the original app).
    habitat = max(0.0, min(100.0, (ndvi_mean + 1.0) * 50.0))
    risk = 100.0 - habitat
    landcover = classify_landcover(ndvi_mean, ndwi_mean, ndbi_mean)

    return {
        "habitat": habitat,
        "risk": risk,
        "ndvi_mean": ndvi_mean,
        "ndwi_mean": ndwi_mean,
        "ndbi_mean": ndbi_mean,
        # Extra vegetation / moisture / burn indices (means).
        "indices": {
            "evi": round(m(idx["evi"]), 4),
            "savi": round(m(idx["savi"]), 4),
            "ndmi": round(m(idx["ndmi"]), 4),
            "nbr": round(m(idx["nbr"]), 4),
        },
        "landcover": landcover,
        "images": {
            "rgb": rgb_to_png_b64(rgb),
            "ndvi": array_to_png_b64(idx["ndvi"], "RdYlGn", -1, 1),
            "ndwi": array_to_png_b64(idx["ndwi"], "Blues", -1, 1),
            "ndbi": array_to_png_b64(idx["ndbi"], "PuOr", -1, 1),
            "evi": array_to_png_b64(idx["evi"], "RdYlGn", -1, 1),
            "ndmi": array_to_png_b64(idx["ndmi"], "BrBG", -1, 1),
            "nbr": array_to_png_b64(idx["nbr"], "RdYlGn", -1, 1),
        },
    }


# ----------------------------------------------------------------------------
# Image encoding (colormap -> base64 PNG data URI)
# ----------------------------------------------------------------------------
def _png_data_uri(rgb_uint8):
    img = Image.fromarray(rgb_uint8, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def array_to_png_b64(arr, cmap_name, vmin, vmax, upscale=2):
    """Apply a matplotlib colormap to a 2-D array and return a PNG data URI."""
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    cmap = cm.get_cmap(cmap_name)
    rgba = cmap(norm(np.nan_to_num(arr, nan=vmin)))
    rgb_uint8 = (rgba[..., :3] * 255).astype(np.uint8)
    if upscale > 1:
        img = Image.fromarray(rgb_uint8).resize(
            (rgb_uint8.shape[1] * upscale, rgb_uint8.shape[0] * upscale),
            Image.NEAREST,
        )
        rgb_uint8 = np.asarray(img)
    return _png_data_uri(rgb_uint8)


def rgb_to_png_b64(rgb01, upscale=2):
    """Encode a float RGB array (0..1) as a PNG data URI."""
    rgb_uint8 = (np.clip(rgb01, 0, 1) * 255).astype(np.uint8)
    if upscale > 1:
        img = Image.fromarray(rgb_uint8).resize(
            (rgb_uint8.shape[1] * upscale, rgb_uint8.shape[0] * upscale),
            Image.BILINEAR,
        )
        rgb_uint8 = np.asarray(img)
    return _png_data_uri(rgb_uint8)


# ----------------------------------------------------------------------------
# Weather
# ----------------------------------------------------------------------------
def get_weather(lat, lon):
    """Return current weather JSON from OpenWeather, or None if unavailable."""
    if not OPENWEATHER_API_KEY:
        return None
    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def get_place_name(lat, lon):
    """
    Reverse-geocode (lat, lon) to a human-readable place name using the Mapbox
    token (already available server-side). Returns a string like
    "Karimnagar, Telangana, India" or None if unavailable.
    """
    if not MAPBOX_ACCESS_TOKEN:
        return None
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lon},{lat}.json"
    try:
        r = requests.get(
            url,
            params={"access_token": MAPBOX_ACCESS_TOKEN, "limit": 1, "language": "en"},
            timeout=8,
        )
        if r.status_code != 200:
            return None
        feats = r.json().get("features") or []
        if feats:
            return feats[0].get("place_name") or feats[0].get("text")
    except (requests.RequestException, ValueError):
        return None
    return None


# ----------------------------------------------------------------------------
# GBIF — real bird occurrence data (keyless, public API)
# ----------------------------------------------------------------------------
def get_bird_observations(lat, lon, radius_km=15, sample=300):
    """
    Query GBIF for recorded bird (Aves) occurrences near a point. Returns a
    dict with the total occurrence count, sampled species richness and the
    most-frequent species, or None if unavailable. Grounds the 'bird' claim in
    real sightings rather than an NDVI proxy alone.
    """
    try:
        params = {
            "taxonKey": 212,               # Aves (birds)
            "hasCoordinate": "true",
            "geoDistance": f"{lat},{lon},{radius_km}km",
            "limit": sample,
        }
        r = requests.get(
            "https://api.gbif.org/v1/occurrence/search", params=params, timeout=10
        )
        if r.status_code != 200:
            return None
        data = r.json()
        results = data.get("results", []) or []
        counter = Counter()
        for rec in results:
            name = rec.get("species") or rec.get("scientificName")
            if name:
                counter[name] += 1
        top = [{"name": n, "count": c} for n, c in counter.most_common(8)]
        return {
            "count": int(data.get("count", 0)),
            "sampled": len(results),
            "species_richness": len(counter),
            "top_species": top,
            "radius_km": radius_km,
        }
    except (requests.RequestException, ValueError):
        return None


# ----------------------------------------------------------------------------
# Sentinel-2 scene metadata (acquisition date + cloud cover) via STAC catalog
# ----------------------------------------------------------------------------
def get_scene_metadata(lat, lon, token, bbox_size=0.01, days=120):
    """
    Query the Sentinel Hub STAC catalog for the most recent scene covering the
    point and return {'date': 'YYYY-MM-DD', 'cloud_cover': float|None}, or None.
    """
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    bbox = [lon - bbox_size, lat - bbox_size, lon + bbox_size, lat + bbox_size]
    payload = {
        "bbox": bbox,
        "datetime": f"{start.strftime('%Y-%m-%dT00:00:00Z')}/{end.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "collections": ["sentinel-2-l2a"],
        "limit": 10,
    }
    try:
        r = requests.post(
            _SENTINEL_CATALOG_URL, json=payload,
            headers={"Authorization": f"Bearer {token}"}, timeout=15,
        )
        if r.status_code != 200:
            return None
        feats = r.json().get("features") or []
        best = None
        for f in feats:
            props = f.get("properties", {})
            dt = props.get("datetime")
            if not dt:
                continue
            if best is None or dt > best["_dt"]:
                cc = props.get("eo:cloud_cover")
                best = {"_dt": dt, "date": dt[:10],
                        "cloud_cover": round(float(cc), 1) if cc is not None else None}
        if best:
            best.pop("_dt", None)
        return best
    except (requests.RequestException, ValueError):
        return None


# ----------------------------------------------------------------------------
# Request guard: optional origin check + best-effort in-memory rate limiting
# ----------------------------------------------------------------------------
_ALLOWED_ORIGIN_HOSTS = [h.strip().lower() for h in _env("ALLOWED_ORIGIN_HOSTS", "").split(",") if h.strip()]
_RATE_LIMIT_PER_MIN = int(_env("RATE_LIMIT_PER_MIN", "60") or "60")
_rate_state = {}  # ip -> (count, window_start)


def _client_ip(handler):
    fwd = handler.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    try:
        return handler.client_address[0]
    except Exception:  # noqa: BLE001
        return "unknown"


def _origin_ok(handler):
    # Only enforced when ALLOWED_ORIGIN_HOSTS is configured (opt-in for prod).
    if not _ALLOWED_ORIGIN_HOSTS:
        return True
    origin = handler.headers.get("Origin") or handler.headers.get("Referer") or ""
    if not origin:
        return True  # same-origin GETs / server-side callers send no Origin
    from urllib.parse import urlparse
    host = (urlparse(origin).hostname or "").lower()
    if host in ("localhost", "127.0.0.1"):
        return True
    return any(host == h or host.endswith("." + h) for h in _ALLOWED_ORIGIN_HOSTS)


def guard_request(handler):
    """Origin check + best-effort per-IP rate limit. Raises ApiError on block."""
    if not _origin_ok(handler):
        raise ApiError("Forbidden origin.", status=403)
    if _RATE_LIMIT_PER_MIN <= 0:
        return
    ip = _client_ip(handler)
    now = time.time()
    count, window_start = _rate_state.get(ip, (0, now))
    if now - window_start > 60:
        count, window_start = 0, now
    count += 1
    _rate_state[ip] = (count, window_start)
    if count > _RATE_LIMIT_PER_MIN:
        raise ApiError("Rate limit exceeded — please slow down and retry shortly.", status=429)


# ----------------------------------------------------------------------------
# Best-effort in-memory TTL cache (per warm serverless instance)
# ----------------------------------------------------------------------------
_cache = OrderedDict()
_CACHE_MAX = 64
_CACHE_TTL = int(_env("CACHE_TTL_SECONDS", "600") or "600")


def cache_get(key):
    item = _cache.get(key)
    if not item:
        return None
    ts, value = item
    if time.time() - ts > _CACHE_TTL:
        _cache.pop(key, None)
        return None
    _cache.move_to_end(key)
    return value


def cache_put(key, value):
    _cache[key] = (time.time(), value)
    _cache.move_to_end(key)
    while len(_cache) > _CACHE_MAX:
        _cache.popitem(last=False)


# ----------------------------------------------------------------------------
# HTTP helpers for BaseHTTPRequestHandler-based endpoints
# ----------------------------------------------------------------------------
def read_json_body(handler):
    """Parse and return the JSON request body as a dict (or {})."""
    length = int(handler.headers.get("Content-Length", 0) or 0)
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise ApiError("Invalid JSON request body.", status=400)


def send_json(handler, obj, status=200):
    body = json.dumps(obj).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def send_error_json(handler, exc):
    status = getattr(exc, "status", 500)
    message = getattr(exc, "message", str(exc))
    send_json(handler, {"error": message}, status=status)


def parse_query(handler):
    """Return a dict of query-string parameters from the request path."""
    from urllib.parse import urlparse, parse_qs

    qs = urlparse(handler.path).query
    return {k: v[0] for k, v in parse_qs(qs).items()}
