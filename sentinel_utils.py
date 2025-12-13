import requests
import numpy as np
from config import SENTINEL_CLIENT_ID, SENTINEL_CLIENT_SECRET


# ---------------- GET SENTINEL-HUB OAUTH TOKEN ---------------- #
def get_sentinel_token():
    url = "https://services.sentinel-hub.com/oauth/token"
    payload = {
        "client_id": SENTINEL_CLIENT_ID,
        "client_secret": SENTINEL_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }
    r = requests.post(url, data=payload)
    r.raise_for_status()
    return r.json()["access_token"]


# ---------------- FIXED EVALSCRIPT (ONLY SAFE BANDS) ---------------- #
EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: ["B02", "B03", "B04", "B08", "B11"],
    output: {
      id: "default",
      bands: 5,
      sampleType: "FLOAT32"
    }
  };
}

function evaluatePixel(sample) {
  return [sample.B02, sample.B03, sample.B04, sample.B08, sample.B11];
}
"""


# ---------------- INTERNAL FUNCTION ---------------- #
def _sentinel_request(lat, lon, token, date=None):
    """
    date=None  → latest available tile
    date="2024-01-15" → specific date
    """

    # 256x256 crop around clicked point
    bbox_size = 0.0025
    bbox = [
        lon - bbox_size,
        lat - bbox_size,
        lon + bbox_size,
        lat + bbox_size,
    ]

    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "input": {
            "bounds": {
                "bbox": bbox,
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
            },
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "maxCloudCoverage": 30,
                        **({"timeRange": {"from": f"{date}T00:00:00Z", "to": f"{date}T23:59:59Z"}}
                           if date else {})
                    },
                }
            ],
        },
        "output": {
            "width": 256,
            "height": 256,
        },
        "evalscript": EVALSCRIPT,
    }

    url = "https://services.sentinel-hub.com/api/v1/process"

    r = requests.post(url, json=payload, headers=headers)
    
    if r.status_code != 200:
        raise RuntimeError(f"SentinelHub Error {r.status_code}: {r.text}")

    # Return array (H,W,5)
    img = np.frombuffer(r.content, dtype=np.float32)
    img = img.reshape((256, 256, 5))

    return img


# ---------------- PUBLIC FUNCTIONS ---------------- #

def fetch_sentinel_tile(lat, lon, token):
    """Fetch latest Sentinel-2 tile"""
    return _sentinel_request(lat, lon, token, date=None)


def fetch_sentinel_tile_on_date(lat, lon, token, date):
    """Fetch Sentinel tile on a specific date (YYYY-MM-DD)"""
    return _sentinel_request(lat, lon, token, date=date)
