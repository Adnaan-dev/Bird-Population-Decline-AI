import os, sys, json, threading, importlib.util
from http.server import HTTPServer
import numpy as np
import requests

os.environ["MAPBOX_ACCESS_TOKEN"] = "pk.test"
os.environ["OPENWEATHER_API_KEY"] = "test"
os.environ["SENTINEL_CLIENT_ID"] = "test"
os.environ["SENTINEL_CLIENT_SECRET"] = "test"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))
import _utils as u

# ---- mock all external network so we test wiring only ----
u.get_sentinel_token = lambda: "FAKE"
def fake_tile(lat, lon, token, dt=None, bbox=None, **k):
    rng = np.random.default_rng(1)
    t = rng.random((6, 48, 48)).astype(np.float32) * 0.3
    t[3] += 0.6; t[2] *= 0.2
    return t
u.fetch_sentinel_tile = fake_tile
u.get_weather = lambda lat, lon: {"main": {"temp": 25, "humidity": 70, "pressure": 1010,
    "feels_like": 26}, "weather": [{"main": "Clear", "description": "clear sky"}],
    "wind": {"speed": 2.0}, "clouds": {"all": 5}}
u.get_place_name = lambda lat, lon: "Test City, Test Region, Testland"
u.get_bird_observations = lambda lat, lon: {"count": 1234, "sampled": 50,
    "species_richness": 12, "top_species": [{"name": "Corvus splendens", "count": 9}],
    "radius_km": 15}
u.get_scene_metadata = lambda lat, lon, token: {"date": "2024-05-01", "cloud_cover": 7.3}

def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join("api", name + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m

results = []
def check(cond, msg):
    print(("PASS" if cond else "FAIL"), "-", msg)
    results.append(cond)

def serve(handler_cls):
    srv = HTTPServer(("127.0.0.1", 0), handler_cls)
    threading.Thread(target=srv.handle_request, daemon=True).start()
    return srv.server_address[1], srv

# ---- config GET ----
cfg = load("config")
port, _ = serve(cfg.handler)
r = requests.get(f"http://127.0.0.1:{port}/api/config", timeout=5)
check(r.status_code == 200, "config GET 200")
check(r.json().get("mapboxToken") == "pk.test", "config returns mapboxToken")

# ---- analyze POST ----
an = load("analyze")
port, _ = serve(an.handler)
r = requests.post(f"http://127.0.0.1:{port}/api/analyze",
                  json={"lat": 14.13, "lon": 74.24}, timeout=10)
check(r.status_code == 200, "analyze POST 200")
d = r.json()
check(all(k in d for k in ["habitat", "risk", "ndvi_mean", "landcover", "images", "weather"]),
      "analyze returns full payload")
check(d["images"]["rgb"].startswith("data:image/png"), "analyze returns RGB data URI")
check(d["weather"]["main"]["temp"] == 25, "analyze includes weather")
check(d.get("place") == "Test City, Test Region, Testland", "analyze returns place name")
check("indices" in d and all(k in d["indices"] for k in ["evi", "savi", "ndmi", "nbr"]),
      "analyze returns extra indices")
check(d.get("birds", {}).get("count") == 1234, "analyze returns bird observations")
check(d.get("scene", {}).get("date") == "2024-05-01", "analyze returns scene metadata")
check(all(k in d["images"] for k in ["evi", "ndmi", "nbr"]), "analyze returns extra heatmaps")

# ---- analyze POST bad body ----
port, _ = serve(load("analyze").handler)
r = requests.post(f"http://127.0.0.1:{port}/api/analyze", json={"lat": "x"}, timeout=5)
check(r.status_code == 400, "analyze bad input -> 400")

# ---- weather GET ----
wx = load("weather")
port, _ = serve(wx.handler)
r = requests.get(f"http://127.0.0.1:{port}/api/weather?lat=14&lon=74", timeout=5)
check(r.status_code == 200 and r.json().get("available") is True, "weather GET returns data")

# ---- timeseries POST ----
ts = load("timeseries")
port, _ = serve(ts.handler)
r = requests.post(f"http://127.0.0.1:{port}/api/timeseries",
                  json={"lat": 14.13, "lon": 74.24, "start": "2024-01-01", "end": "2024-04-01"},
                  timeout=15)
check(r.status_code == 200, "timeseries POST 200")
tsd = r.json()
check(len(tsd["dates"]) == len(tsd["values"]) and len(tsd["values"]) > 0, "timeseries returns aligned series")
check("stats" in tsd and "anomaly" in tsd["stats"], "timeseries returns baseline/anomaly stats")

# ---- change POST ----
cg = load("change")
port, _ = serve(cg.handler)
r = requests.post(f"http://127.0.0.1:{port}/api/change",
                  json={"lat": 14.13, "lon": 74.24, "date1": "2023-01-15", "date2": "2024-01-15"},
                  timeout=15)
check(r.status_code == 200, "change POST 200")
cd = r.json()
check("ndvi_delta" in cd and cd["images"]["diff"].startswith("data:image/png"),
      "change returns delta + diff map")

# ---- report POST ----
rp = load("report")
port, _ = serve(rp.handler)
r = requests.post(f"http://127.0.0.1:{port}/api/report",
                  json={"lat": 14.13, "lon": 74.24, "habitat": 67.5, "risk": 32.5,
                        "ndvi_mean": 0.35, "landcover": "Cropland",
                        "weather": u.get_weather(0, 0)}, timeout=10)
check(r.status_code == 200, "report POST 200")
check(r.headers.get("Content-Type") == "application/pdf", "report returns application/pdf")
check(r.content[:4] == b"%PDF", "report body is a PDF")

print("\nRESULT:", "ALL PASS" if all(results) else f"{results.count(False)} FAILURE(S)")
sys.exit(0 if all(results) else 1)
