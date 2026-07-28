"""
POST /api/analyze  { "lat": <float>, "lon": <float>, "bbox": [w,s,e,n]? }

Fetches a Sentinel-2 tile at the location (or over a drawn bbox), computes
NDVI/NDWI/NDBI + EVI/SAVI/NDMI/NBR, habitat health + bird-decline risk,
land-cover, RGB + index heatmaps (base64 PNG), current weather, the resolved
place name, real bird occurrences (GBIF), and the source scene metadata.
"""
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.append(os.path.dirname(__file__))
import _utils as u


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            u.guard_request(self)
            body = u.read_json_body(self)
            try:
                lat = float(body["lat"])
                lon = float(body["lon"])
            except (KeyError, TypeError, ValueError):
                raise u.ApiError("Request must include numeric 'lat' and 'lon'.", status=400)

            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise u.ApiError("Coordinates out of range.", status=400)

            # Optional bbox for area analysis: [west, south, east, north]
            bbox = body.get("bbox")
            bbox_key = "pt"
            if bbox is not None:
                try:
                    bbox = [float(v) for v in bbox]
                    assert len(bbox) == 4
                except Exception:
                    raise u.ApiError("Invalid 'bbox' (expected [w,s,e,n]).", status=400)
                bbox_key = ",".join(f"{v:.3f}" for v in bbox)

            cache_key = f"analyze:{round(lat, 3)},{round(lon, 3)}:{bbox_key}"
            cached = u.cache_get(cache_key)
            if cached is not None:
                return u.send_json(self, cached)

            token = u.get_sentinel_token()
            tile = u.fetch_sentinel_tile(lat, lon, token, bbox=bbox)
            result = u.analyze_tile(tile)

            result["lat"] = lat
            result["lon"] = lon
            result["bbox"] = bbox
            result["place"] = u.get_place_name(lat, lon)
            result["weather"] = u.get_weather(lat, lon)
            result["birds"] = u.get_bird_observations(lat, lon)
            result["scene"] = u.get_scene_metadata(lat, lon, token)
            u.cache_put(cache_key, result)
            u.send_json(self, result)
        except u.ApiError as exc:
            u.send_error_json(self, exc)
        except Exception as exc:  # noqa: BLE001
            u.send_error_json(self, u.ApiError(f"Analysis failed: {exc}", status=500))

    def log_message(self, *args):
        pass
