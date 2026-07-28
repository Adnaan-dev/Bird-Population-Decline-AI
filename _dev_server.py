"""
Local dev server that mirrors the Vercel setup (static files + /api/* Python
functions) so the app can be tested in a browser without the Vercel CLI.

Usage:  python _dev_server.py   ->  http://127.0.0.1:3000
"""
import os
import sys
import posixpath
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.join(ROOT, "api")

# 1) Load .env into the environment BEFORE importing the api modules
#    (they bind module-level config from os.environ at import time).
env_path = os.path.join(ROOT, ".env")
if os.path.exists(env_path):
    for line in open(env_path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# 2) Import the serverless handlers.
sys.path.insert(0, API_DIR)
import config as api_config          # noqa: E402
import analyze as api_analyze        # noqa: E402
import weather as api_weather        # noqa: E402
import timeseries as api_timeseries  # noqa: E402
import report as api_report          # noqa: E402
import change as api_change          # noqa: E402

API_ROUTES = {
    "/api/config": api_config.handler,
    "/api/analyze": api_analyze.handler,
    "/api/weather": api_weather.handler,
    "/api/timeseries": api_timeseries.handler,
    "/api/report": api_report.handler,
    "/api/change": api_change.handler,
}

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".webmanifest": "application/manifest+json",
}


class DevHandler(BaseHTTPRequestHandler):
    def _api_path(self):
        return self.path.split("?", 1)[0]

    def do_GET(self):
        path = self._api_path()
        target = API_ROUTES.get(path)
        if target is not None:
            return target.do_GET(self)
        return self._serve_static()

    def do_POST(self):
        path = self._api_path()
        target = API_ROUTES.get(path)
        if target is not None:
            return target.do_POST(self)
        self.send_error(404, "Not found")

    # --- static file serving -------------------------------------------------
    def _serve_static(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            path = "/index.html"

        rel = posixpath.normpath(path).lstrip("/")
        fs_path = os.path.join(ROOT, *rel.split("/"))

        # Clean-URL rewrite: /methodology -> methodology.html (mirrors vercel.json)
        if not os.path.isfile(fs_path) and not os.path.splitext(fs_path)[1]:
            html_candidate = fs_path + ".html"
            if os.path.isfile(html_candidate):
                fs_path = html_candidate

        # keep inside project root
        if not os.path.abspath(fs_path).startswith(ROOT):
            self.send_error(403, "Forbidden")
            return
        if not os.path.isfile(fs_path):
            return self._serve_404()

        ext = os.path.splitext(fs_path)[1].lower()
        ctype = CONTENT_TYPES.get(ext, "application/octet-stream")
        with open(fs_path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_404(self):
        page = os.path.join(ROOT, "404.html")
        if os.path.isfile(page):
            with open(page, "rb") as f:
                data = f.read()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404, "Not found")

    def log_message(self, fmt, *args):
        sys.stderr.write("[dev] %s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "3000"))
    httpd = ThreadingHTTPServer(("127.0.0.1", port), DevHandler)
    print(f"Local dev server running at http://127.0.0.1:{port}")
    print("  /            -> index.html")
    print("  /dashboard   -> dashboard.html")
    print("  /api/*       -> Python serverless handlers")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
        httpd.shutdown()
