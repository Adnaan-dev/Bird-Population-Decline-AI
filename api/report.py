"""
POST /api/report  -> application/pdf

Body: { lat, lon, habitat, risk, ndvi_mean, landcover, weather }
Generates the habitat analysis PDF report (same content as the original app).
"""
import os
import sys
import unicodedata
from datetime import datetime
from http.server import BaseHTTPRequestHandler

from fpdf import FPDF
from fpdf.enums import XPos, YPos

sys.path.append(os.path.dirname(__file__))
import _utils as u

# ---- Brand palette (RGB) -------------------------------------------------
HEADER_BG = (15, 23, 42)     # slate-900 (brand dark)
EMERALD   = (16, 185, 129)
CYAN      = (6, 182, 212)
GREEN     = (22, 163, 74)
AMBER     = (217, 119, 6)
RED       = (220, 38, 38)
DARK      = (30, 41, 59)      # body text
MUTED     = (100, 116, 139)   # labels / secondary
BORDER    = (214, 222, 233)
ROW_BG    = (244, 247, 251)
CARD_BG   = (247, 250, 253)
WHITE     = (255, 255, 255)

# ---- Page geometry -------------------------------------------------------
PW = 210.0        # A4 width (mm)
LM = 14.0         # left margin
RM = 14.0         # right margin
CW = PW - LM - RM # content width


def _latin(text):
    """
    Make text safe for fpdf2 core fonts (latin-1). Transliterates accents to
    ASCII where possible and drops characters that cannot be represented
    (e.g. Arabic / Devanagari), so the PDF never crashes on non-Latin names.
    """
    if not text:
        return ""
    norm = unicodedata.normalize("NFKD", str(text))
    out = norm.encode("latin-1", "ignore").decode("latin-1")
    # collapse artefacts left by dropped characters
    out = " ".join(out.replace(" ,", ",").split())
    return out.strip(" ,")


class ReportPDF(FPDF):
    def footer(self):
        self.set_y(-16)
        self.set_draw_color(*BORDER)
        self.set_line_width(0.2)
        self.line(LM, self.get_y(), PW - RM, self.get_y())
        self.ln(1.5)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*MUTED)
        self.cell(0, 4,
                  "Bird Population Decline AI  -  Satellite-based habitat analysis  -  "
                  "For research & education; validate with domain expertise.",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.set_font("Helvetica", "", 7.5)
        self.cell(0, 4, f"Page {self.page_no()}", align="C")


def _status_health(v):
    return ("Healthy", GREEN) if v > 60 else ("Moderate", AMBER) if v > 30 else ("Critical", RED)


def _status_risk(v):
    return ("High", RED) if v > 60 else ("Medium", AMBER) if v > 30 else ("Low", GREEN)


def _status_veg(v):
    return ("Excellent", GREEN) if v > 0.5 else ("Good", AMBER) if v > 0.2 else ("Poor", RED)


def build_pdf(lat, lon, habitat, risk, ndvi_mean, landcover, weather, place=None):
    pdf = ReportPDF(format="A4")
    pdf.set_title("Bird Habitat Analysis Report")
    pdf.set_author("Bird Population Decline AI")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(LM, 14, RM)
    pdf.add_page()

    # ---- helpers ---------------------------------------------------------
    def section(title):
        pdf.ln(2.2)
        y = pdf.get_y()
        pdf.set_fill_color(*EMERALD)
        pdf.rect(LM, y + 0.6, 3, 5.6, style="F")          # left accent bar
        pdf.set_xy(LM + 6, y)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 7, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        yy = pdf.get_y() + 0.3
        pdf.set_draw_color(*BORDER)
        pdf.set_line_width(0.3)
        pdf.line(LM, yy, PW - RM, yy)
        pdf.ln(1.8)

    def kv(label, value, idx, value_color=DARK):
        y = pdf.get_y()
        pdf.set_fill_color(*(ROW_BG if idx % 2 == 0 else WHITE))
        pdf.set_x(LM)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*MUTED)
        pdf.cell(58, 6.4, f"   {label}", border=0, fill=True)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(*value_color)
        pdf.cell(CW - 58, 6.4, str(value), border=0, fill=True,
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def scorecard(x, w, label, big, sub, color):
        y = pdf.get_y()
        h = 23.0
        pdf.set_fill_color(*CARD_BG)
        pdf.rect(x, y, w, h, style="F")
        pdf.set_fill_color(*color)
        pdf.rect(x, y, w, 2.4, style="F")                 # top accent strip
        pdf.set_xy(x, y + 4.2)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*MUTED)
        pdf.cell(w, 4, label.upper(), align="C")
        pdf.set_xy(x, y + 9.0)
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(*color)
        pdf.cell(w, 8, big, align="C")
        pdf.set_xy(x, y + 17.2)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*MUTED)
        pdf.cell(w, 4, sub, align="C")

    def bullet(text, color):
        y = pdf.get_y()
        pdf.set_fill_color(*color)
        pdf.ellipse(LM + 1.2, y + 1.5, 1.8, 1.8, style="F")
        pdf.set_x(LM + 6)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(*DARK)
        pdf.multi_cell(0, 4.8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ---- header band -----------------------------------------------------
    pdf.set_fill_color(*HEADER_BG)
    pdf.rect(0, 0, PW, 34, style="F")
    pdf.set_fill_color(*EMERALD)
    pdf.rect(0, 34, PW, 1.6, style="F")                    # accent underline
    pdf.set_xy(0, 8)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 9, "Bird Population Decline AI", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(0)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(125, 211, 192)
    pdf.cell(0, 6, "Bird Habitat Analysis Report", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(0)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 5, f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", align="C")
    pdf.set_y(42)

    # ---- score cards -----------------------------------------------------
    h_label, h_color = _status_health(habitat)
    r_label, r_color = _status_risk(risk)
    v_label, v_color = _status_veg(ndvi_mean)
    gap = 6.0
    cw3 = (CW - 2 * gap) / 3.0
    y0 = pdf.get_y()
    scorecard(LM, cw3, "Habitat Health", f"{habitat:.1f}", f"out of 100  -  {h_label}", h_color)
    pdf.set_y(y0)
    scorecard(LM + cw3 + gap, cw3, "Bird Decline Risk", f"{risk:.1f}", f"out of 100  -  {r_label}", r_color)
    pdf.set_y(y0)
    scorecard(LM + 2 * (cw3 + gap), cw3, "Mean NDVI", f"{ndvi_mean:.3f}", f"vegetation  -  {v_label}", v_color)
    pdf.set_y(y0 + 23.0)

    # ---- location --------------------------------------------------------
    section("Location Details")
    lat_h = "N" if lat >= 0 else "S"
    lon_h = "E" if lon >= 0 else "W"
    place_txt = _latin(place)
    kv("Location Name", place_txt if place_txt else "Unnamed / remote area", 0)
    kv("Latitude", f"{abs(lat):.5f} deg {lat_h}", 1)
    kv("Longitude", f"{abs(lon):.5f} deg {lon_h}", 0)
    kv("Coordinates", f"{lat:.5f}, {lon:.5f}", 1)

    # ---- habitat analysis ------------------------------------------------
    section("Habitat Analysis Results")
    kv("Habitat Health", f"{habitat:.1f} / 100  ({h_label})", 0, h_color)
    kv("Bird Decline Risk", f"{risk:.1f} / 100  ({r_label})", 1, r_color)
    kv("Mean NDVI", f"{ndvi_mean:.3f}  ({v_label})", 0, v_color)
    kv("Land-Cover Class", str(landcover), 1)

    # ---- weather ---------------------------------------------------------
    if weather:
        wm = weather.get("main", {})
        wd = (weather.get("weather") or [{}])[0]
        wind = weather.get("wind", {}).get("speed", "N/A")
        clouds = weather.get("clouds", {}).get("all", "N/A")
        section("Weather Conditions")
        kv("Temperature", f"{wm.get('temp', 'N/A')} C  (feels {wm.get('feels_like', 'N/A')} C)", 0)
        kv("Humidity", f"{wm.get('humidity', 'N/A')} %", 1)
        kv("Pressure", f"{wm.get('pressure', 'N/A')} hPa", 0)
        kv("Conditions", str(wd.get("main", "N/A")), 1)
        kv("Wind / Clouds", f"{wind} m/s  /  {clouds} % cover", 0)

    # ---- satellite -------------------------------------------------------
    section("Sentinel-2 Satellite Data")
    kv("Source", "Sentinel-2 MSI (ESA / Copernicus)", 0)
    kv("Indices", "NDVI (vegetation), NDWI (water), NDBI (built-up)", 1)
    kv("Resolution", "10 - 60 m per pixel", 0)

    # ---- summary ---------------------------------------------------------
    section("Analysis Summary")
    b1 = ("Excellent vegetation coverage.", GREEN) if habitat > 70 else \
         ("Moderate vegetation coverage.", AMBER) if habitat > 40 else \
         ("Low vegetation coverage - attention needed.", RED)
    b2 = ("Low bird-population-decline risk.", GREEN) if risk < 30 else \
         ("Moderate decline risk - consider monitoring.", AMBER) if risk < 70 else \
         ("High decline risk - action recommended.", RED)
    b3 = ("Healthy vegetation density detected.", GREEN) if ndvi_mean > 0.4 else \
         ("Moderate vegetation with mixed land cover.", AMBER) if ndvi_mean > 0.2 else \
         ("Low vegetation - urban / sparse area.", RED)
    for text, color in (b1, b2, b3):
        bullet(text, color)

    # ---- recommendations -------------------------------------------------
    section("Recommendations")
    for rec in [
        "Monitor this location regularly to detect change over time.",
        "Validate findings with ground-truth field observations.",
        "Consider conservation measures if decline risk is elevated.",
        "Integrate with other ecological and species datasets.",
    ]:
        bullet(rec, CYAN)

    return bytes(pdf.output())


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            u.guard_request(self)
            b = u.read_json_body(self)
            pdf_bytes = build_pdf(
                lat=float(b.get("lat", 0.0)),
                lon=float(b.get("lon", 0.0)),
                habitat=float(b.get("habitat", 0.0)),
                risk=float(b.get("risk", 0.0)),
                ndvi_mean=float(b.get("ndvi_mean", 0.0)),
                landcover=str(b.get("landcover", "N/A")),
                weather=b.get("weather"),
                place=b.get("place"),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", 'attachment; filename="habitat_report.pdf"')
            self.send_header("Content-Length", str(len(pdf_bytes)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(pdf_bytes)
        except u.ApiError as exc:
            u.send_error_json(self, exc)
        except Exception as exc:  # noqa: BLE001
            u.send_error_json(self, u.ApiError(f"Report generation failed: {exc}", status=500))

    def log_message(self, *args):
        pass
