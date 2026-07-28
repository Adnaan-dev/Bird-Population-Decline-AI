"""GET /api/weather?lat=<>&lon=<>  -> current weather JSON (or {available:false})."""
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.append(os.path.dirname(__file__))
import _utils as u


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            u.guard_request(self)
            q = u.parse_query(self)
            try:
                lat = float(q["lat"])
                lon = float(q["lon"])
            except (KeyError, TypeError, ValueError):
                raise u.ApiError("Query must include numeric 'lat' and 'lon'.", status=400)

            weather = u.get_weather(lat, lon)
            if weather is None:
                u.send_json(self, {"available": False})
            else:
                u.send_json(self, {"available": True, "weather": weather})
        except u.ApiError as exc:
            u.send_error_json(self, exc)
        except Exception as exc:  # noqa: BLE001
            u.send_error_json(self, u.ApiError(f"Weather lookup failed: {exc}", status=500))

    def log_message(self, *args):
        pass
