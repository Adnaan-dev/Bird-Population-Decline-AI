"""GET /api/config -> public client configuration (Mapbox token)."""
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.append(os.path.dirname(__file__))
import _utils as u


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            u.guard_request(self)
            u.send_json(self, {
                "mapboxToken": u.MAPBOX_ACCESS_TOKEN,
                "weatherEnabled": bool(u.OPENWEATHER_API_KEY),
                "sentinelConfigured": bool(u.SENTINEL_CLIENT_ID and u.SENTINEL_CLIENT_SECRET),
            })
        except u.ApiError as exc:
            u.send_error_json(self, exc)

    def log_message(self, *args):  # silence default stderr logging
        pass
