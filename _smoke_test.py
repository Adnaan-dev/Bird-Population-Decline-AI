import os, sys, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))

import numpy as np
import tifffile
import _utils as u
import importlib.util

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

failures = []
def check(cond, msg):
    print(("PASS" if cond else "FAIL"), "-", msg)
    if not cond: failures.append(msg)

# ---- synthetic 6-band tile (B02,B03,B04,B08,B11,B12), 64x64 ----
rng = np.random.default_rng(0)
tile = rng.random((6, 64, 64)).astype(np.float32) * 0.3
# make NIR (idx3) high and red (idx2) low -> healthy vegetation
tile[3] += 0.6
tile[2] *= 0.2

# ---- compute_indices ----
ndvi, ndwi, ndbi = u.compute_indices(tile)
check(ndvi.shape == (64, 64), "compute_indices returns HxW")
check(-1.0 <= float(np.nanmean(ndvi)) <= 1.0, "NDVI mean in [-1,1]")
check(float(np.nanmean(ndvi)) > 0.2, "high-NIR tile yields positive NDVI")

# ---- make_rgb ----
rgb = u.make_rgb(tile)
check(rgb.shape == (64, 64, 3), "make_rgb returns HxWx3")
check(rgb.min() >= 0 and rgb.max() <= 1, "RGB normalized 0..1")

# ---- classify_landcover ----
check(u.classify_landcover(0.8, -0.5, -0.3) == "Dense Forest / Vegetation", "dense forest classification")
check(u.classify_landcover(0.1, 0.5, 0.2) == "Water / Wetland", "water classification")
check(u.classify_landcover(0.1, -0.4, 0.3) == "Urban / Built-up", "urban classification")

# ---- analyze_tile ----
res = u.analyze_tile(tile)
for k in ["habitat", "risk", "ndvi_mean", "ndwi_mean", "ndbi_mean", "landcover", "images", "indices"]:
    check(k in res, f"analyze_tile has key '{k}'")
check(0 <= res["habitat"] <= 100, "habitat in [0,100]")
check(abs(res["habitat"] + res["risk"] - 100) < 1e-6, "habitat + risk == 100")
for ik in ["evi", "savi", "ndmi", "nbr"]:
    check(ik in res["indices"], f"indices has '{ik}'")
for img_key in ["rgb", "ndvi", "ndwi", "ndbi", "evi", "ndmi", "nbr"]:
    uri = res["images"][img_key]
    check(uri.startswith("data:image/png;base64,"), f"{img_key} is PNG data URI")
    check(len(uri) > 200, f"{img_key} data URI non-trivial length")

# ---- compute_all_indices robust to 5-band tiles ----
tile5 = tile[:5]
idx5 = u.compute_all_indices(tile5)
check(all(k in idx5 for k in ["ndvi", "evi", "savi", "ndmi", "nbr"]), "compute_all_indices works on 5-band")

# ---- _to_chw handles (H,W,C) ----
hwc = np.transpose(tile, (1, 2, 0))
back = u._to_chw(hwc, nbands=6)
check(back.shape == (6, 64, 64), "_to_chw converts (H,W,C)->(C,H,W)")

# ---- tifffile round-trip (simulates Sentinel TIFF parse path) ----
buf = io.BytesIO()
tifffile.imwrite(buf, np.transpose(tile, (1, 2, 0)))  # write as (H,W,C)
buf.seek(0)
parsed = tifffile.imread(buf).astype(np.float32)
parsed = u._to_chw(parsed, nbands=6)
check(parsed.shape == (6, 64, 64), "tifffile round-trip -> (6,64,64)")

# ---- PDF report ----
report = load_module("report_mod", os.path.join("api", "report.py"))
pdf_bytes = report.build_pdf(
    lat=14.13, lon=74.24, habitat=res["habitat"], risk=res["risk"],
    ndvi_mean=res["ndvi_mean"], landcover=res["landcover"],
    weather={"main": {"temp": 27, "humidity": 80, "pressure": 1008},
             "weather": [{"main": "Clouds"}], "wind": {"speed": 3.1}, "clouds": {"all": 40}},
)
check(pdf_bytes[:4] == b"%PDF", "PDF starts with %PDF header")
check(len(pdf_bytes) > 1000, "PDF has reasonable size")

# ---- PDF with no weather ----
pdf2 = report.build_pdf(1.0, 2.0, 50.0, 50.0, 0.3, "Cropland", None)
check(pdf2[:4] == b"%PDF", "PDF (no weather) valid")

print("\nRESULT:", "ALL PASS" if not failures else f"{len(failures)} FAILURE(S): {failures}")
sys.exit(1 if failures else 0)
