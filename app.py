import streamlit as st
import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms as T
from PIL import Image
import requests
import matplotlib.pyplot as plt
from datetime import date, timedelta

from fpdf import FPDF
import folium
from streamlit_folium import st_folium
from folium.raster_layers import TileLayer
from rasterio.io import MemoryFile

# st.markdown(open("ui_styles.css").read(), unsafe_allow_html=True)


# ---------------- CONFIG: API KEYS ----------------
MAPBOX_ACCESS_TOKEN = "pk.eyJ1IjoiYWRuYW55dDc2IiwiYSI6ImNtaWpjejk1MjB6YzMzZnF4bGNkc2I4d3cifQ.4ZzJfUkNdID5dz5D1cXMFw"
OPENWEATHER_API_KEY = "1bff769b3f43bb1470ffbfe9ffc05fdb"
SENTINEL_CLIENT_ID = "8add0ed6-799f-43ea-80d5-0869c963f9ee"
SENTINEL_CLIENT_SECRET = "qzQmOA7aGHmQX7EH6MnogkbAv4W45eeY"

# Streamlit page
st.set_page_config(page_title="Bird Population Decline AI", layout="wide", initial_sidebar_state="expanded")

# Import ResNet18 with weights to avoid deprecation warning
from torchvision.models import resnet18, ResNet18_Weights

# ---------------- CSS: Glassmorphism ----------------
CUSTOM_CSS = """
<style>
* {
    transition: all 0.3s ease;
}

body {
    background: linear-gradient(135deg, #0f172a 0%, #020617 100%);
    color: #e5e7eb;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Main Title */
.main-title {
    font-size: 2.8rem;
    font-weight: 900;
    background: linear-gradient(90deg, #10b981, #06b6d4, #4ade80);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -1px;
    text-shadow: 0 0 30px rgba(16, 185, 129, 0.3);
    margin-bottom: 1rem;
}

/* Glass Card - Info Section */
.glass-card {
    background: rgba(15, 23, 42, 0.65);
    padding: 20px 24px;
    border-radius: 16px;
    border: 1px solid rgba(148, 163, 184, 0.3);
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(10px);
    margin-bottom: 1.5rem;
}

.glass-card:hover {
    border-color: rgba(148, 163, 184, 0.5);
    box-shadow: 0 25px 60px rgba(0, 0, 0, 0.5);
    transform: translateY(-2px);
}

/* Metric Boxes - Data Display */
.metric-box {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(6, 182, 212, 0.15));
    padding: 20px 16px;
    border-radius: 14px;
    border: 2px solid rgba(16, 185, 129, 0.4);
    text-align: center;
    box-shadow: 0 10px 30px rgba(16, 185, 129, 0.15);
    backdrop-filter: blur(8px);
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.metric-box:hover {
    transform: translateY(-8px) scale(1.03);
    box-shadow: 0 20px 45px rgba(16, 185, 129, 0.25);
    border-color: rgba(16, 185, 129, 0.7);
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.25), rgba(6, 182, 212, 0.25));
}

.metric-title {
    font-size: 0.8rem;
    color: #a5b4c3;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
}

.metric-value {
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(90deg, #10b981, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* Data Section Cards */
.data-section {
    background: rgba(20, 30, 50, 0.75);
    padding: 26px 28px;
    border-radius: 18px;
    border: 1px solid rgba(96, 165, 250, 0.3);
    box-shadow: 0 15px 45px rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(12px);
    margin: 1.5rem 0;
}

.data-section:hover {
    border-color: rgba(96, 165, 250, 0.5);
    box-shadow: 0 20px 55px rgba(0, 0, 0, 0.5);
}

.section-title {
    font-size: 1.4rem;
    font-weight: 700;
    color: #06b6d4;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 2px solid rgba(6, 182, 212, 0.3);
}

/* Subheading Styling */
h2 {
    color: #10b981;
    font-size: 1.3rem;
    margin-top: 1.5rem;
    margin-bottom: 0.75rem;
}

# ---- Enhanced Sidebar Styling ----
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.95), rgba(10, 15, 35, 0.9));
    backdrop-filter: blur(20px);
    border-right: 1px solid rgba(96, 165, 250, 0.2);
    box-shadow: 2px 0 25px rgba(0, 0, 0, 0.3);
}

[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] .css-18ni7ap {
    color: #06b6d4 !important;
    font-weight: 700;
    font-size: 1.1rem;
}

[data-testid="stSidebar"] button,
[data-testid="stSidebar"] .stRadio,
[data-testid="stSidebar"] label {
    color: #e5e7eb !important;
}

[data-testid="stSidebar"] .stRadio label {
    padding: 0.8rem !important;
    border-radius: 8px;
    transition: all 0.3s ease;
}

[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(16, 185, 129, 0.1);
    color: #10b981 !important;
}

# ---- Navigation Bar Styling ----
.stTabs [role="tablist"] {
    background: rgba(20, 30, 50, 0.7);
    border-bottom: 2px solid rgba(96, 165, 250, 0.2);
    border-radius: 12px 12px 0 0;
    padding: 0.5rem;
}

.stTabs [aria-selected="true"] {
    border-bottom: 3px solid #10b981 !important;
}

.stTabs [role="tab"] {
    color: #9ca3af !important;
    padding: 0.75rem 1.5rem !important;
    font-weight: 600;
    transition: all 0.3s ease;
}

.stTabs [role="tab"]:hover {
    color: #06b6d4 !important;
    background: rgba(6, 182, 212, 0.1);
    border-radius: 8px;
}

.stTabs [aria-selected="true"] {
    color: #10b981 !important;
    background: rgba(16, 185, 129, 0.1);
}

/* Footer */
.footer {
    margin-top: 24px;
    text-align: center;
    font-size: 0.85rem;
    color: #6b7280;
    padding: 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
}

/* Info Box */
.info-box {
    background: rgba(59, 130, 246, 0.1);
    border-left: 4px solid #3b82f6;
    padding: 14px 16px;
    border-radius: 8px;
    margin: 12px 0;
    font-size: 0.95rem;
    line-height: 1.6;
}

/* Matplotlib Figures Styling */
.stPyplot {
    background: transparent !important;
}

.stPyplot canvas {
    background: rgba(15, 23, 42, 0.5) !important;
    border-radius: 12px;
    border: 1px solid rgba(96, 165, 250, 0.2);
}

/* Success/Warning Styling */
.stSuccess {
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.5);
}

.stWarning {
    background: rgba(251, 146, 60, 0.15);
    border: 1px solid rgba(251, 146, 60, 0.5);
}

.stError {
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.5);
}

/* Loading Spinner */
.stSpinner {
    color: #10b981 !important;
}

.stSpinner > div {
    border-color: rgba(16, 185, 129, 0.3) !important;
    border-top-color: #10b981 !important;
}

/* Download Button */
.stDownloadButton button {
    background: linear-gradient(90deg, #10b981, #06b6d4) !important;
    border: none !important;
    color: white !important;
    font-weight: 700 !important;
}

.stDownloadButton button:hover {
    box-shadow: 0 8px 25px rgba(16, 185, 129, 0.3) !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------- SIMPLE LOGIN ----------------
DEFAULT_USER = "admin"
DEFAULT_PASS = "ecoscope"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login_screen():
    # Centered login container
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("", unsafe_allow_html=True)  # Spacing
        st.markdown(
            "<div style='text-align: center; margin-bottom: 2rem;'>"
            "<h1 class='main-title'>Bihanga Drushti 🛰️🌿</h1>"
            "</div>", 
            unsafe_allow_html=True
        )
        
        st.markdown(
            "<div class='glass-card' style='text-align: center; padding: 2.5rem;'>"
            "<h2 style='color: #06b6d4; margin-bottom: 1rem; font-size: 1.6rem;'>Secure Login</h2>"
            "<p style='color: #d1d5db; margin-bottom: 1.5rem; font-size: 0.95rem;'>"
            "Demo Credentials:<br/><b style='color: #10b981; font-size: 1.1rem;'>admin</b> / <b style='color: #10b981; font-size: 1.1rem;'>ecoscope</b>"
            "</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        
        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        
        user = st.text_input("👤 Username", key="username_input", placeholder="Enter username")
        pwd = st.text_input("🔒 Password", type="password", key="password_input", placeholder="Enter password")
        
        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        
        col_btn1, col_btn2, col_btn3 = st.columns([1.2, 1.6, 1.2])
        with col_btn2:
            if st.button("🚀 Login", use_container_width=True, type="primary"):
                if user == DEFAULT_USER and pwd == DEFAULT_PASS:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials. Please try again.")
        
        st.markdown(
            "<div style='text-align: center; margin-top: 3rem; color: #6b7280; font-size: 0.85rem;'>"
            "<p>🌍 Satellite Intelligence for Bird Habitat Monitoring</p>"
            "<p style='font-size: 0.8rem; margin-top: 1rem; opacity: 0.7;'>Powered by Sentinel-2 & AI</p>"
            "</div>",
            unsafe_allow_html=True,
        )

if not st.session_state.logged_in:
    login_screen()
    raise SystemExit

# ---------------- SENTINEL HUB HELPERS ----------------

# Evalscript: return 4 bands (B02,B03,B04,B08) as float32
EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{
      bands: ["B02","B03","B04","B08"],
      units: "REFLECTANCE"
    }],
    output: {
      bands: 4,
      sampleType: "FLOAT32"
    }
  };
}
function evaluatePixel(sample) {
  return [sample.B02, sample.B03, sample.B04, sample.B08];
}
"""

@st.cache_data(show_spinner=False)
def get_sentinel_token():
    url = "https://services.sentinel-hub.com/oauth/token"
    payload = {
        "client_id": SENTINEL_CLIENT_ID,
        "client_secret": SENTINEL_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }
    r = requests.post(url, data=payload, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]

def fetch_sentinel_tile(lat, lon, token, dt=None):
    """
    Fetch a Sentinel-2 tile around (lat,lon).
    If dt is None → latest available. Otherwise dt = "YYYY-MM-DD".
    """
    bbox_size = 0.01  # roughly ~1km
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
                "properties": {
                    "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
                },
            },
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": data_filter,
                }
            ],
        },
        "evalscript": EVALSCRIPT,
        "output": {
            "width": 256,
            "height": 256,
            "responses": [
                {"identifier": "default", "format": {"type": "image/tiff"}}
            ],
        },
    }

    url = "https://services.sentinel-hub.com/api/v1/process"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(url, json=payload, headers=headers, timeout=60)

    if r.status_code != 200:
        raise RuntimeError(f"SentinelHub Error {r.status_code}: {r.text}")

    # Read GeoTIFF from bytes
    with MemoryFile(r.content) as memfile:
        with memfile.open() as ds:
            arr = ds.read().astype(np.float32)  # shape: (4, H, W)

    return arr  # (4,H,W) B02,B03,B04,B08

# ---------------- WEATHER ----------------
def get_weather(lat, lon):
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
    except Exception:
        return None

# ---------------- MODEL (ResNet18 demo) ----------------
@st.cache_resource(show_spinner=False)
def load_model():
    # Use weights parameter instead of deprecated pretrained parameter
    model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
    # replace last layer with 3-class head (Forest / Urban / Water-ish)
    model.fc = nn.Linear(512, 3)  # randomly initialized, demo only
    model.eval()
    return model

MODEL = load_model()
TRANSFORM = T.Compose([
    T.ToPILImage(),
    T.Resize((224, 224)),
    T.ToTensor(),
    T.Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225]),
])
CLASS_NAMES = ["Forest-like", "Urban-like", "Water/Other"]

# ---------------- INDICES ----------------
def make_rgb(tile):
    # tile: (4,H,W) → (H,W,3)
    b02, b03, b04, b08 = tile
    rgb = np.stack([b04, b03, b02], axis=-1)  # R,G,B
    rgb = np.clip((rgb - rgb.min()) / (rgb.max() - rgb.min() + 1e-6), 0, 1)
    return rgb

def compute_indices(tile):
    b02, b03, b04, b08 = tile
    red = b04
    nir = b08
    green = b03
    eps = 1e-6
    ndvi = (nir - red) / (nir + red + eps)
    ndwi = (green - nir) / (green + nir + eps)
    # fake SWIR ~ average of red+nir
    swir = (red + nir) / 2.0
    ndbi = (swir - nir) / (swir + nir + eps)
    return ndvi, ndwi, ndbi

def predict_habitat_and_risk(tile):
    rgb = make_rgb(tile)
    ndvi, ndwi, ndbi = compute_indices(tile)
    ndvi_mean = float(np.nanmean(ndvi))

    # Heuristic: NDVI -1..1 → 0..100 habitat health
    habitat_score = max(0.0, min(100.0, (ndvi_mean + 1) * 50))
    risk_score = 100.0 - habitat_score

    # CNN demo classification
    img_t = TRANSFORM((rgb * 255).astype(np.uint8)).unsqueeze(0)
    with torch.no_grad():
        logits = MODEL(img_t)
        pred_idx = int(torch.argmax(logits, dim=1).item())
    landcover = CLASS_NAMES[pred_idx]

    return habitat_score, risk_score, landcover, rgb, ndvi, ndwi, ndbi, ndvi_mean

# ---------------- PDF REPORT ----------------
def generate_pdf(lat, lon, habitat, risk, ndvi_mean, landcover, weather):
    from datetime import datetime
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=12)
    
    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Bird Population Decline AI", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Bird Habitat Analysis Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    
    # Separator line
    pdf.ln(2)
    pdf.set_draw_color(100, 100, 100)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    
    # Location Details Section
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(20, 120, 130)
    pdf.cell(0, 7, "Location Details", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, f"Latitude: {lat:.5f} degrees North", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 5, f"Longitude: {lon:.5f} degrees East", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 5, f"Coordinates: {lat:.5f}°N, {lon:.5f}°E", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Habitat Analysis Section
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(20, 120, 130)
    pdf.cell(0, 7, "Habitat Analysis Results", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    
    health_status = "Healthy" if habitat > 60 else "Moderate" if habitat > 30 else "Critical"
    risk_status = "High" if risk > 60 else "Medium" if risk > 30 else "Low"
    veg_status = "Excellent" if ndvi_mean > 0.5 else "Good" if ndvi_mean > 0.2 else "Poor"
    
    pdf.cell(0, 5, f"Habitat Health: {habitat:.1f}/100 ({health_status})", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 5, f"Bird Decline Risk: {risk:.1f}/100 ({risk_status})", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 5, f"Mean NDVI: {ndvi_mean:.3f} ({veg_status})", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 5, f"Land-Cover: {landcover}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Weather Information Section
    if weather:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(20, 120, 130)
        pdf.cell(0, 7, "Weather Conditions", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 9)
        
        weather_main = weather['main']
        weather_desc = weather['weather'][0]
        
        pdf.cell(0, 5, f"Temperature: {weather_main['temp']}°C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 5, f"Humidity: {weather_main['humidity']}%", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 5, f"Pressure: {weather_main.get('pressure', 'N/A')} hPa", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 5, f"Weather: {weather_desc['main']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        wind_speed = weather.get('wind', {}).get('speed', 'N/A')
        cloudiness = weather.get('clouds', {}).get('all', 'N/A')
        pdf.cell(0, 5, f"Wind: {wind_speed} m/s, Clouds: {cloudiness}%", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Satellite Data Section
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(20, 120, 130)
    pdf.cell(0, 7, "Sentinel-2 Satellite Data", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 8)
    
    sat_text = (
        "Source: Sentinel-2 MSI | NDVI: Vegetation | NDWI: Water | NDBI: Built-up | "
        "Resolution: 10-60m"
    )
    pdf.multi_cell(0, 4, sat_text)
    
    # Interpretation Section
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(20, 120, 130)
    pdf.cell(0, 7, "Analysis Summary", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 9)
    
    # Build interpretation
    interp = []
    if habitat > 70:
        interp.append("Excellent vegetation coverage.")
    elif habitat > 40:
        interp.append("Moderate vegetation coverage.")
    else:
        interp.append("Low vegetation coverage - Attention needed.")
    
    if risk < 30:
        interp.append("Low bird population decline risk.")
    elif risk < 70:
        interp.append("Moderate decline risk - Consider monitoring.")
    else:
        interp.append("High decline risk - Action recommended.")
    
    if ndvi_mean > 0.4:
        interp.append("Healthy vegetation density detected.")
    elif ndvi_mean > 0.2:
        interp.append("Moderate vegetation with mixed land cover.")
    else:
        interp.append("Low vegetation - Urban/sparse area.")
    
    for text in interp:
        pdf.multi_cell(0, 4, f"• {text}")
    
    # Recommendations Section
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(20, 120, 130)
    pdf.cell(0, 7, "Recommendations", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 8)
    
    recommendations = [
        "Monitor location regularly for changes",
        "Validate with ground truth observations",
        "Consider conservation measures if needed",
        "Integrate with other ecological data"
    ]
    
    for rec in recommendations:
        pdf.multi_cell(0, 4, f"• {rec}")
    
    # Footer
    pdf.ln(2)
    pdf.set_draw_color(100, 100, 100)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 4, "Bird Population Decline AI | Satellite-based Habitat Analysis | For scientific use, validate with domain expertise.")
    
    # Return bytes directly
    pdf_bytes = pdf.output()
    return pdf_bytes

# ---------------- NDVI TIME-SERIES ----------------
def compute_ndvi_timeseries(lat, lon, start_date, end_date):
    token = get_sentinel_token()
    dates = []
    ndvi_means = []
    current = start_date
    step = timedelta(days=30)  # approx monthly

    with st.spinner("📈 Fetching NDVI time-series from Sentinel-2…"):
        while current <= end_date:
            dt_str = current.isoformat()
            try:
                tile = fetch_sentinel_tile(lat, lon, token, dt=dt_str)
                ndvi, _, _ = compute_indices(tile)
                ndvi_means.append(float(np.nanmean(ndvi)))
                dates.append(current)
            except Exception:
                # skip missing/cloudy dates
                pass
            current += step

    return dates, ndvi_means

# ---------------- PAGE 1: MAP ANALYSIS ----------------
def page_map_analysis():
    st.markdown("<h1 class='main-title'>Bird Population Decline AI - Map Analysis</h1>", unsafe_allow_html=True)
    st.markdown(
        "<div class='glass-card'>"
        "Click anywhere on the map to fetch Sentinel-2 imagery, compute NDVI/NDWI/NDBI, "
        "estimate habitat health and bird population decline risk, and generate a PDF report."
        "</div>",
        unsafe_allow_html=True,
    )

    center = [20.0, 78.0]
    m = folium.Map(location=center, zoom_start=4, tiles=None)
    TileLayer(
        tiles=f"https://api.mapbox.com/styles/v1/mapbox/satellite-streets-v12/tiles/{{z}}/{{x}}/{{y}}?access_token={MAPBOX_ACCESS_TOKEN}",
        attr="Mapbox",
        name="Mapbox Satellite",
        max_zoom=19,
        tile_size=512,
        zoom_offset=-1,
    ).add_to(m)
    m.add_child(folium.LatLngPopup())

    map_state = st_folium(m, width=800, height=500)

    if map_state and map_state.get("last_clicked"):
        lat = map_state["last_clicked"]["lat"]
        lon = map_state["last_clicked"]["lng"]

        st.session_state.last_lat = lat
        st.session_state.last_lon = lon

        st.markdown(
            "<div class='data-section'><div class='section-title'>📍 Selected Location Details</div>"
            f"<div class='info-box'><b>Coordinates:</b> {lat:.5f}°N, {lon:.5f}°E</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        if st.button("🔎 Analyze this location", type="primary", use_container_width=True):
            try:
                token = get_sentinel_token()
                with st.spinner("🛰️ Fetching Sentinel-2 tile and running analysis..."):
                    tile = fetch_sentinel_tile(lat, lon, token)
                    habitat, risk, landcover, rgb, ndvi, ndwi, ndbi, ndvi_mean = predict_habitat_and_risk(tile)

                # Key Metrics Section
                st.markdown("<div class='data-section'><div class='section-title'>📊 Key Metrics</div>", unsafe_allow_html=True)
                c1, c2, c3 = st.columns(3)
                with c1:
                    health_status = "✅ Healthy" if habitat > 60 else "⚠️ Moderate" if habitat > 30 else "❌ Critical"
                    st.markdown(
                        f"<div class='metric-box'><div class='metric-title'>🌿 Habitat Health</div>"
                        f"<div class='metric-value'>{habitat:.1f}</div>"
                        f"<div style='color: #9ca3af; font-size: 0.8rem; margin-top: 0.5rem;'>{health_status}</div></div>",
                        unsafe_allow_html=True,
                    )
                with c2:
                    risk_status = "🔴 High" if risk > 60 else "🟡 Medium" if risk > 30 else "🟢 Low"
                    st.markdown(
                        f"<div class='metric-box'><div class='metric-title'>🦅 Bird Decline Risk</div>"
                        f"<div class='metric-value'>{risk:.1f}</div>"
                        f"<div style='color: #9ca3af; font-size: 0.8rem; margin-top: 0.5rem;'>{risk_status}</div></div>",
                        unsafe_allow_html=True,
                    )
                with c3:
                    ndvi_status = "🟢 Excellent" if ndvi_mean > 0.5 else "🟡 Good" if ndvi_mean > 0.2 else "🔴 Poor"
                    st.markdown(
                        f"<div class='metric-box'><div class='metric-title'>📈 Mean NDVI</div>"
                        f"<div class='metric-value'>{ndvi_mean:.3f}</div>"
                        f"<div style='color: #9ca3af; font-size: 0.8rem; margin-top: 0.5rem;'>{ndvi_status} Vegetation</div></div>",
                        unsafe_allow_html=True,
                    )
                st.markdown("</div>", unsafe_allow_html=True)

                # Satellite Imagery Section
                st.markdown("<div class='data-section'><div class='section-title'>🛰️ Satellite and Vegetation Indices</div>", unsafe_allow_html=True)
                st.markdown(
                    "<div class='info-box'>"
                    "<b>RGB:</b> True color composite | "
                    "<b>NDVI:</b> Vegetation health (Red-Yellow-Green) | "
                    "<b>NDWI:</b> Water content (Blue scale) | "
                    "<b>NDBI:</b> Built-up areas (Purple scale)"
                    "</div>",
                    unsafe_allow_html=True,
                )
                fig, ax = plt.subplots(1, 4, figsize=(18, 4))
                fig.patch.set_facecolor((0, 0, 0, 0))
                ax[0].imshow(rgb); ax[0].set_title("RGB", fontsize=12, color='white', fontweight='bold'); ax[0].axis("off")
                ax[1].imshow(ndvi, cmap="RdYlGn", vmin=-1, vmax=1); ax[1].set_title("NDVI", fontsize=12, color='white', fontweight='bold'); ax[1].axis("off")
                ax[2].imshow(ndwi, cmap="Blues", vmin=-1, vmax=1); ax[2].set_title("NDWI", fontsize=12, color='white', fontweight='bold'); ax[2].axis("off")
                ax[3].imshow(ndbi, cmap="PuOr", vmin=-1, vmax=1); ax[3].set_title("NDBI", fontsize=12, color='white', fontweight='bold'); ax[3].axis("off")
                st.pyplot(fig)
                st.markdown("</div>", unsafe_allow_html=True)

                # Land Cover Section
                st.markdown("<div class='data-section'><div class='section-title'>Land-Cover Classification</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='info-box'><b>Predicted Land-Cover Type:</b> {landcover}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

                # Weather Section
                weather = get_weather(lat, lon)
                if weather:
                    st.markdown("<div class='data-section'><div class='section-title'>🌦️ Weather Information</div>", unsafe_allow_html=True)
                    
                    weather_main = weather['main']
                    weather_desc = weather['weather'][0]
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(
                            f"<div class='metric-box'><div class='metric-title'>🌡️ Temperature</div>"
                            f"<div class='metric-value'>{weather_main['temp']}°C</div>"
                            f"<div style='color: #9ca3af; font-size: 0.8rem; margin-top: 0.5rem;'>Feels like {weather_main.get('feels_like', 'N/A')}°C</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    with col2:
                        st.markdown(
                            f"<div class='metric-box'><div class='metric-title'>💧 Humidity</div>"
                            f"<div class='metric-value'>{weather_main['humidity']}%</div>"
                            f"<div style='color: #9ca3af; font-size: 0.8rem; margin-top: 0.5rem;'>Pressure: {weather_main.get('pressure', 'N/A')} hPa</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    with col3:
                        st.markdown(
                            f"<div class='metric-box'><div class='metric-title'>⛅ Conditions</div>"
                            f"<div class='metric-value' style='font-size: 0.95rem'>{weather_desc['main']}</div>"
                            f"<div style='color: #9ca3af; font-size: 0.8rem; margin-top: 0.5rem;'>{weather_desc['description'].title()}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    
                    col4, col5 = st.columns(2)
                    with col4:
                        wind_speed = weather.get('wind', {}).get('speed', 'N/A')
                        st.markdown(
                            f"<div class='metric-box'><div class='metric-title'>💨 Wind Speed</div>"
                            f"<div class='metric-value'>{wind_speed} m/s</div></div>",
                            unsafe_allow_html=True,
                        )
                    with col5:
                        cloudiness = weather.get('clouds', {}).get('all', 'N/A')
                        st.markdown(
                            f"<div class='metric-box'><div class='metric-title'>☁️ Cloud Cover</div>"
                            f"<div class='metric-value'>{cloudiness}%</div></div>",
                            unsafe_allow_html=True,
                        )
                    
                    st.markdown("</div>", unsafe_allow_html=True)

            except Exception as e:
                st.error(f"During analysis: {e}")

# ---------------- PAGE 2: NDVI TIME-SERIES ----------------
def page_ndvi_series():
    st.markdown("<h1 class='main-title'>NDVI Time-Series Analysis</h1>", unsafe_allow_html=True)

    if "last_lat" not in st.session_state:
        st.warning("First select a location in the Map Analysis page.")
        return

    lat = st.session_state.last_lat
    lon = st.session_state.last_lon

    st.markdown(
        f"<div class='glass-card'>Using last selected location: Lat {lat:.5f}, Lon {lon:.5f}</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='data-section'><div class='section-title'>Select Date Range</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("Start date", value=date.today() - timedelta(days=365))
    with c2:
        end_date = st.date_input("End date", value=date.today())

    if start_date > end_date:
        st.error("Start date must be before end date.")
        return

    if st.button("📈 Compute NDVI Trend"):
        dates, values = compute_ndvi_timeseries(lat, lon, start_date, end_date)
        if not dates:
            st.error("No NDVI data found (clouds / missing imagery). Try a different period.")
            return

        st.markdown("<div class='data-section'><div class='section-title'>NDVI Time-Series Graph</div>", unsafe_allow_html=True)
        fig, ax = plt.subplots(figsize=(12, 5))
        fig.patch.set_facecolor((0, 0, 0, 0))
        ax.set_facecolor((0.05, 0.08, 0.15, 0.7))
        ax.plot(dates, values, marker="o", linewidth=2.5, markersize=8, color='#10b981')
        ax.set_xlabel("Date", fontsize=11, color='#e5e7eb')
        ax.set_ylabel("Mean NDVI", fontsize=11, color='#e5e7eb')
        ax.set_title("NDVI Time-Series from Sentinel-2", fontsize=13, color='#10b981', fontweight='bold')
        ax.grid(True, alpha=0.2, color='#e5e7eb')
        ax.tick_params(colors='#e5e7eb')
        st.pyplot(fig)
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- PAGE 3: ABOUT ----------------
def page_about():
    st.markdown("<h1 class='main-title'>About Bird Population Decline AI</h1>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class='glass-card'>
        <b>Bird Population Decline AI</b> is a research-oriented demo that shows how you can:
        <ul>
          <li>Use Sentinel-2 satellite imagery (via Sentinel Hub) to monitor habitats</li>
          <li>Compute NDVI / NDWI / NDBI from MSI bands</li>
          <li>Feed satellite patches to a CNN (ResNet18) for land-cover cues</li>
          <li>Score habitat health and bird decline risk heuristically from NDVI</li>
          <li>Explore NDVI time-series to detect gradual habitat loss</li>
          <li>Generate PDF reports for documentation and decision support</li>
        </ul>
        For serious use, replace the demo CNN + heuristic scoring with your
        own trained model on EuroSAT / BigEarthNet / bird datasets.
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown(
        """
        <div class='data-section'>
        <div class='section-title'>Technology Stack</div>
        <div class='info-box'>
        <b>Remote Sensing:</b> Sentinel-2 MSI via Sentinel Hub API
        </div>
        <div class='info-box'>
        <b>Deep Learning:</b> PyTorch ResNet18 for land-cover classification
        </div>
        <div class='info-box'>
        <b>Web Framework:</b> Streamlit for rapid dashboard development
        </div>
        <div class='info-box'>
        <b>Geospatial Tools:</b> Folium, Mapbox for interactive mapping
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------- MAIN APP ----------------
def main():
    # Enhanced Sidebar Navigation
    with st.sidebar:
        st.markdown(
            "<div style='text-align: center; margin-bottom: 2rem;'>"
            "<h2 style='color: #06b6d4; margin: 0;'>🧭 Navigation</h2>"
            "<p style='color: #9ca3af; font-size: 0.85rem; margin-top: 0.5rem;'>Select a module below</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        
        page = st.radio(
            "Module Selection",
            ["📍 Map Analysis", "📈 NDVI Time-Series", "ℹ️ About"],
            label_visibility="collapsed",
        )
        
        st.markdown(
            "<div style='margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid rgba(255, 255, 255, 0.1);'>"
            "<p style='color: #6b7280; font-size: 0.8rem; text-align: center;'>"
            "🌍 Satellite Intelligence<br/>for Habitat Monitoring"
            "</p></div>",
            unsafe_allow_html=True,
        )

    # Route to selected page
    if "Map Analysis" in page:
        page_map_analysis()
    elif "NDVI Time-Series" in page:
        page_ndvi_series()
    else:
        page_about()

    st.markdown(
        "<div class='footer'>"
        "Made by Adnan with ❤️ using Streamlit, Sentinel Hub & PyTorch<br/>"
        "<span style='font-size: 0.8rem; opacity: 0.7;'>Bird Population Decline AI v2.0</span>"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
