"""Vercel serverless function: POST /api/dispatch (also served at /dispatch via vercel.json rewrite)."""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _core import cors_headers, handle_dispatch  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def _send(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        for k, v in cors_headers(self.headers.get("Origin", "")).items():
            self.send_header(k, v)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in cors_headers(self.headers.get("Origin", "")).items():
            self.send_header(k, v)
        self.end_headers()

    def do_POST(self):
        length = min(int(self.headers.get("Content-Length", 0) or 0), 8192)
        raw = self.rfile.read(length).decode("utf-8", errors="replace") if length else "{}"
        client_ip = (self.headers.get("x-forwarded-for", "") or self.client_address[0]).split(",")[0].strip()
        status, payload = handle_dispatch(raw, client_ip)
        self._send(status, payload)

    def do_GET(self):
        self._send(405, {"status": "error", "error": "Use POST."})
