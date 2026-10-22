"""Vercel serverless function: GET /api/health (also served at /health via vercel.json rewrite)."""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _core import cors_headers  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in cors_headers(self.headers.get("Origin", "")).items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        configured = all(os.environ.get(k) for k in ("GMAIL_USER", "GMAIL_APP_PASSWORD", "DEMO_PASSCODE"))
        body = json.dumps({
            "status": "ok" if configured else "misconfigured",
            "service": "ECE441-IoT-Alert-Gateway (hosted)",
        }).encode("utf-8")
        self.send_response(200 if configured else 503)
        for k, v in cors_headers(self.headers.get("Origin", "")).items():
            self.send_header(k, v)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)
