"""
POST /api/change  { "lat", "lon", "date1": "YYYY-MM-DD", "date2": "YYYY-MM-DD" }

Fetches Sentinel-2 tiles for two dates, computes NDVI for each, and returns a
diverging NDVI-difference map (date2 - date1) plus summary statistics that
quantify vegetation loss / gain between the two dates.
"""
import os
import sys
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler

import numpy as np

sys.path.append(os.path.dirname(__file__))
import _utils as u


def _parse(value, field):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise u.ApiError(f"Invalid '{field}' date (expected YYYY-MM-DD).", status=400)


def _ndvi_for_window(lat, lon, token, center, half_days=8):
    """Try a small +/- window around a date to find a usable low-cloud scene."""
    for delta in range(0, half_days + 1):
        for sign in ((0,) if delta == 0 else (-1, 1)):
            d = (center + timedelta(days=sign * delta)).isoformat()
            try:
                tile = u.fetch_sentinel_tile(lat, lon, token, dt=d)
                ndvi, _, _ = u.compute_indices(tile)
                return ndvi, d
            except u.ApiError:
                continue
    return None, None


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

            d1 = _parse(body.get("date1"), "date1")
            d2 = _parse(body.get("date2"), "date2")
            if d1 == d2:
                raise u.ApiError("Pick two different dates.", status=400)
            if d1 > d2:
                d1, d2 = d2, d1

            token = u.get_sentinel_token()
            ndvi1, used1 = _ndvi_for_window(lat, lon, token, d1)
            ndvi2, used2 = _ndvi_for_window(lat, lon, token, d2)
            if ndvi1 is None or ndvi2 is None:
                raise u.ApiError(
                    "Could not find usable low-cloud imagery near one or both dates. "
                    "Try dates further apart or a clearer season.",
                    status=502,
                )

            diff = ndvi2 - ndvi1
            mean1 = float(np.nanmean(ndvi1))
            mean2 = float(np.nanmean(ndvi2))
            frac_loss = float(np.mean(diff < -0.1))
            frac_gain = float(np.mean(diff > 0.1))

            u.send_json(self, {
                "lat": lat, "lon": lon,
                "date1": used1, "date2": used2,
                "ndvi_mean_1": round(mean1, 4),
                "ndvi_mean_2": round(mean2, 4),
                "ndvi_delta": round(mean2 - mean1, 4),
                "pct_vegetation_loss": round(frac_loss * 100, 1),
                "pct_vegetation_gain": round(frac_gain * 100, 1),
                "images": {
                    "ndvi1": u.array_to_png_b64(ndvi1, "RdYlGn", -1, 1),
                    "ndvi2": u.array_to_png_b64(ndvi2, "RdYlGn", -1, 1),
                    "diff": u.array_to_png_b64(diff, "RdBu", -1, 1),
                },
            })
        except u.ApiError as exc:
            u.send_error_json(self, exc)
        except Exception as exc:  # noqa: BLE001
            u.send_error_json(self, u.ApiError(f"Change detection failed: {exc}", status=500))

    def log_message(self, *args):
        pass
