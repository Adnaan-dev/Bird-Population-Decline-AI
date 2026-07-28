"""
POST /api/timeseries  { "lat", "lon", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" }

Samples the Sentinel-2 archive at ~monthly steps between start and end and
returns the mean NDVI for each date that has usable (low-cloud) imagery.
"""
import os
import sys
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler

import numpy as np

sys.path.append(os.path.dirname(__file__))
import _utils as u

MAX_STEPS = 24  # safety cap on API calls within the function time budget


def _parse_date(value, field):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise u.ApiError(f"Invalid '{field}' date (expected YYYY-MM-DD).", status=400)


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

            start = _parse_date(body.get("start"), "start")
            end = _parse_date(body.get("end"), "end")
            if start > end:
                raise u.ApiError("'start' must be on or before 'end'.", status=400)

            token = u.get_sentinel_token()
            dates, values = [], []
            current = start
            step = timedelta(days=30)
            steps = 0

            while current <= end and steps < MAX_STEPS:
                dt_str = current.isoformat()
                try:
                    tile = u.fetch_sentinel_tile(lat, lon, token, dt=dt_str)
                    ndvi, _, _ = u.compute_indices(tile)
                    values.append(round(float(np.nanmean(ndvi)), 4))
                    dates.append(dt_str)
                except u.ApiError:
                    pass  # skip cloudy / missing dates
                current += step
                steps += 1

            stats = {}
            if values:
                arr = np.array(values, dtype=float)
                mean = float(arr.mean())
                std = float(arr.std())
                latest = float(values[-1])
                stats = {
                    "mean": round(mean, 4),
                    "std": round(std, 4),
                    "min": round(float(arr.min()), 4),
                    "max": round(float(arr.max()), 4),
                    "latest": round(latest, 4),
                    "anomaly": round(latest - mean, 4),
                    "baseline_low": round(mean - std, 4),
                    "baseline_high": round(mean + std, 4),
                }

            u.send_json(self, {"lat": lat, "lon": lon, "dates": dates,
                               "values": values, "stats": stats})
        except u.ApiError as exc:
            u.send_error_json(self, exc)
        except Exception as exc:  # noqa: BLE001
            u.send_error_json(self, u.ApiError(f"Time-series failed: {exc}", status=500))

    def log_message(self, *args):
        pass
