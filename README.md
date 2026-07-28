# 🦅 Bird Population Decline AI

> **Geospatial habitat intelligence — a static frontend + Python serverless API, ready to deploy on Vercel.**

Analyze bird habitat health and population-decline risk for any location on Earth
from **Sentinel-2** satellite imagery. Click a point (or draw an area) on the map to
compute a suite of spectral indices, score habitat health and bird-decline risk,
classify land-cover, overlay **real bird sightings (GBIF)**, pull live weather,
compare two dates for vegetation change, chart NDVI over time, and export the results
as a **PDF, CSV or GeoJSON**.

The app is a **static frontend + Python serverless functions** (no build step, no
framework). It deploys on Vercel with zero configuration. The original Streamlit +
PyTorch prototype is archived under [`legacy_streamlit/`](legacy_streamlit/).

---

## 🌟 Features

**Analysis**
- 🗺️ **Interactive map analysis** — click a point or **draw an area** (polygon → bounding box)
- 🌿 **7 spectral indices** — NDVI, NDWI, NDBI, **EVI, SAVI, NDMI, NBR** as color heatmaps
- 🦅 **Habitat health & bird-decline risk** — 0–100 scoring with animated gauges
- 🌍 **Land-cover classification** — Forest / Cropland / Urban / Water / Barren (rule-based)
- 🔀 **Change detection** — pick two dates → NDVI-difference map + % vegetation loss/gain
- 📈 **NDVI time-series** — monthly sampling with a seasonal baseline band + anomaly readout
- 🛰️ **Source-scene metadata** — actual acquisition date & cloud cover of the tile used

**Credibility**
- 🐦 **Real bird data (GBIF)** — observed species count, richness and top species near the point

**UX**
- 🔍 **Place search** (Mapbox geocoding) · ⭐ **saved locations** · 🔗 **shareable permalinks**
- 🌗 **Light/dark theme**, responsive design, keyboard-navigable, reduced-motion aware
- 📄 **Exports** — polished **PDF** report, plus **CSV** and **GeoJSON**
- 🌦️ **Live weather** — temperature, humidity, wind, cloud cover
- 📲 **Installable PWA** with an offline app shell
- 🔓 **Open access** — no login required; anyone can use the dashboard

**Production-readiness**
- 🛡️ Opt-in **origin allow-list** + best-effort **per-IP rate limiting** on the API
- ⚡ In-memory **result caching** (per warm instance) for repeat lookups
- 🐞 Optional **Sentry** error monitoring · ✅ **GitHub Actions CI**

---

## 🏗️ Architecture

```
Browser (static site)                       Vercel Python Serverless Functions
┌────────────────────────────┐             ┌────────────────────────────────────────┐
│ index.html    (landing)    │             │ /api/config      public config          │
│ dashboard.html (app)       │             │ /api/analyze     Sentinel-2 + indices    │
│ methodology / explore /    │   fetch()   │ /api/change      two-date NDVI diff      │
│ about / faq  (content)     │ ──────────► │ /api/timeseries  NDVI series + baseline  │
│ assets/css, assets/js      │             │ /api/weather     OpenWeather proxy       │
│ Mapbox GL JS + GL Draw     │             │ /api/report      PDF report (fpdf2)      │
│ Chart.js · service worker  │             └────────────────────────────────────────┘
└────────────────────────────┘              shared: api/_utils.py
```

- **No PyTorch / rasterio.** Land-cover is derived deterministically from spectral
  indices (remote-sensing conventions), and GeoTIFFs are parsed with pure-Python
  `tifffile` — so the function bundle stays well under Vercel's Python size limit.
- **Secrets stay server-side.** Sentinel + OpenWeather keys are read from environment
  variables and never reach the browser. The Mapbox token is a public client token
  (restrict it by URL in your Mapbox account).

---

## 🔌 API

| Endpoint | Method | Body / Query | Returns |
|---|---|---|---|
| `/api/config` | GET | – | Mapbox token + capability flags |
| `/api/analyze` | POST | `{lat, lon, bbox?}` | indices, scores, land-cover, heatmaps, weather, place, **birds**, **scene** |
| `/api/change` | POST | `{lat, lon, date1, date2}` | NDVI delta, % loss/gain, before/after/diff maps |
| `/api/timeseries` | POST | `{lat, lon, start, end}` | dates + values + baseline/anomaly stats |
| `/api/weather` | GET | `?lat=&lon=` | current weather |
| `/api/report` | POST | metrics `{…, place?}` | PDF (`application/pdf`) |

---

## 🚀 Deploy on Vercel

1. Push this repository to GitHub/GitLab/Bitbucket.
2. In Vercel: **Add New… → Project → Import** the repo. **No build settings needed**
   (zero-config: static files at the root, Python functions in `/api`).
3. Add **Environment Variables** (Project Settings → Environment Variables):

   | Variable | Required | Notes |
   |---|---|---|
   | `MAPBOX_ACCESS_TOKEN` | ✅ | public client token, sent to the browser for the basemap |
   | `SENTINEL_CLIENT_ID` | ✅ | Sentinel Hub / CDSE OAuth client ID |
   | `SENTINEL_CLIENT_SECRET` | ✅ | Sentinel Hub / CDSE OAuth secret |
   | `OPENWEATHER_API_KEY` | ✅ | OpenWeather |
   | `ALLOWED_ORIGIN_HOSTS` | optional | comma-separated hostnames allowed to call the API (e.g. `your-app.vercel.app`). Unset = allow all |
   | `RATE_LIMIT_PER_MIN` | optional | per-IP request cap (default `60`; `0` disables) |
   | `CACHE_TTL_SECONDS` | optional | cache lifetime for repeat analyze calls (default `600`) |
   | `SENTRY_DSN` | optional | enables Sentry error monitoring |
   | `SENTINEL_TOKEN_URL` / `SENTINEL_PROCESS_URL` / `SENTINEL_CATALOG_URL` | optional | override Sentinel endpoints (default to CDSE) |

4. **Deploy.** Landing page at `/`, dashboard at `/dashboard`, content pages at
   `/methodology`, `/explore`, `/about`, `/faq`, and the API at `/api/*`.

### 🔑 Get Sentinel Hub credentials (free via CDSE)

Sentinel Hub access is now provided through the **Copernicus Data Space Ecosystem (CDSE)**:

1. Create a free account at <https://dataspace.copernicus.eu/>.
2. Open the **CDSE Sentinel Hub dashboard** → <https://shapps.dataspace.copernicus.eu/dashboard/>.
3. **User Settings → OAuth clients → Create** (grant type: *Client credentials*).
4. Copy the **Client ID** and **Client Secret** (the secret is shown only once).

The app targets the CDSE endpoints by default. To use the legacy commercial
`services.sentinel-hub.com` deployment instead, set the `SENTINEL_*_URL` overrides.

> 🔐 **Never commit real keys.** `.env` is git-ignored. If any keys ever landed in
> git history, rotate them.

---

## 💻 Local development

```bash
cp .env.example .env     # then fill in your keys

# Option A — mirror production with the Vercel CLI
npm i -g vercel
vercel dev               # static site + /api/* Python functions together

# Option B — no Vercel CLI needed (built-in dev server)
python -m venv .venv && .venv\Scripts\activate   # (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt requests
python _dev_server.py    # http://127.0.0.1:3000  (serves static + /api/*)
```

### Run the automated checks

```bash
python _smoke_test.py     # pipeline: indices, classify, analyze_tile, PDF     (42 checks)
python _http_test.py      # every /api endpoint over HTTP (mocked network)      (21 checks)
```

CI runs both suites plus JS syntax checks on every push (see
[`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

---

## 🔬 Algorithms

```
NDVI = (NIR   - Red)  / (NIR   + Red)     vegetation health   [-1..1]
NDWI = (Green - NIR)  / (Green + NIR)     water content       [-1..1]
NDBI = (SWIR1 - NIR)  / (SWIR1 + NIR)     built-up areas      [-1..1]
EVI  = 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)       enhanced vegetation
SAVI = (NIR - Red) / (NIR + Red + 0.5) * 1.5                  soil-adjusted vegetation
NDMI = (NIR - SWIR1) / (NIR + SWIR1)      vegetation moisture [-1..1]
NBR  = (NIR - SWIR2) / (NIR + SWIR2)      burn / vegetation   [-1..1]

Habitat Health    = clamp((NDVI + 1) * 50, 0, 100)
Bird Decline Risk = 100 - Habitat Health
```

Bands requested from Sentinel-2 L2A: **B02** (Blue), **B03** (Green), **B04** (Red),
**B08** (NIR), **B11** (SWIR1), **B12** (SWIR2).

Land-cover rules: `NDWI > 0.2` → Water/Wetland · `NDBI > 0 and NDVI < 0.3` →
Urban/Built-up · `NDVI ≥ 0.6` → Dense Forest · `NDVI ≥ 0.3` → Moderate
Vegetation/Cropland · else → Barren/Sparse.

> ⚠️ **This is a demonstration / educational tool, not a validated scientific
> instrument.** Scores are index-derived proxies and should not replace field
> ecology or peer-reviewed population studies.

---

## 🛠️ Project structure

```
Bird-Population-Decline-AI/
├── index.html                 # Landing page
├── dashboard.html             # Dashboard (map, change detection, time-series, about)
├── methodology.html           # Pipeline & formulas
├── explore.html               # Example habitats (deep-link into the dashboard)
├── about.html · faq.html      # Content pages
├── 404.html                   # On-brand not-found page
├── manifest.webmanifest       # PWA manifest
├── sw.js                      # PWA service worker (offline shell)
├── assets/
│   ├── css/style.css          # Design system (light/dark, components)
│   ├── js/site.js             # Shared: theme, nav, reveal, accordion, PWA
│   ├── js/dashboard.js        # Dashboard logic (Mapbox, Chart.js, API calls)
│   └── icon.svg               # App icon
├── api/
│   ├── _utils.py              # Shared: Sentinel, indices, GBIF, geocode, cache, guard
│   ├── config.py              # GET  public config
│   ├── analyze.py             # POST lat/lon[/bbox] -> full analysis
│   ├── change.py              # POST two dates -> NDVI change map
│   ├── timeseries.py          # POST date range -> NDVI series + baseline
│   ├── weather.py             # GET  lat/lon -> weather
│   └── report.py              # POST metrics -> PDF
├── requirements.txt           # Serverless deps (numpy, matplotlib, pillow, tifffile, requests, fpdf2)
├── vercel.json                # Functions config + rewrites + headers
├── .vercelignore              # Keeps dev/test/legacy files out of the deploy
├── .env.example               # Environment variable template
├── _dev_server.py             # Local dev server (mirrors Vercel routing)
├── _smoke_test.py · _http_test.py   # Test suites
├── .github/workflows/ci.yml   # CI
└── legacy_streamlit/          # Archived original Streamlit + PyTorch app
```

---

## 🔒 Security notes

- The API is **open** (no login) but hardened: set `ALLOWED_ORIGIN_HOSTS` to your
  domain to reject cross-origin calls, and `RATE_LIMIT_PER_MIN` to throttle abuse.
- All third-party keys live in environment variables; only the public Mapbox token
  reaches the browser. Restrict that token by URL in your Mapbox account.

---

## 📄 License

MIT. See [LICENSE](LICENSE).

Built with ❤️ using Sentinel-2, Mapbox, GBIF, OpenWeather, and Python serverless functions.
