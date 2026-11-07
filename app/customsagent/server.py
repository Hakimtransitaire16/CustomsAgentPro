"""Minimal HTTP server (standard library only).

    python -m customsagent.server            # http://localhost:8000

POST /api/classify  {"description": "..."}
POST /api/analyze   <dossier JSON>
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .engine import Engine

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
# CUSTOMSAGENT_DATA=official -> real DGD tariff and decisions from knowledge-base/
ENGINE = Engine.official() if os.environ.get("CUSTOMSAGENT_DATA") == "official" else Engine()
MAX_BODY = 1_000_000


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, (WEB_DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
        else:
            self._json(404, {"error": "not_found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self._json(413, {"error": "too_large"})
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/classify":
                return self._json(200, {"suggestions": ENGINE.classify(str(data.get("description", "")))})
            if self.path == "/api/analyze":
                return self._json(200, ENGINE.analyze_dict(data))
            return self._json(404, {"error": "not_found"})
        except (ValueError, TypeError, KeyError) as exc:
            return self._json(400, {"error": "bad_request", "detail": str(exc)})

    def log_message(self, fmt, *args):  # quieter logs
        pass


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    print(f"CustomsAgentPro prototype on http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
