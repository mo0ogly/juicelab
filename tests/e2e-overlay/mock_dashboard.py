"""Minimal stand-in for the teacher dashboard sync endpoint.

Accepts the CORS preflight and POST /api/sync that the JuiceLab overlay
sends from the browser, and appends every received event as one JSON line
to the file given on the command line. Used only by the overlay e2e guard
(tests/e2e-overlay/run.sh); it never runs in production.
"""

import json
import logging
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Instance-Label, X-User-Email, X-Student-Token",
}


def make_handler(events_path: str) -> type[BaseHTTPRequestHandler]:
    """Build a request handler class bound to the events output file."""

    class Handler(BaseHTTPRequestHandler):
        def _reply(self, status: int, body: dict) -> None:
            payload = json.dumps(body).encode()
            self.send_response(status)
            for key, value in CORS_HEADERS.items():
                self.send_header(key, value)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_OPTIONS(self) -> None:  # noqa: N802 (http.server naming)
            self._reply(200, {})

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/api/health":
                self._reply(200, {"ok": True})
            else:
                self._reply(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/sync":
                self._reply(404, {"error": "not found"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            event = json.loads(self.rfile.read(length) or b"{}")
            with open(events_path, "a", encoding="utf-8") as out:
                out.write(json.dumps(event) + "\n")
            self._reply(200, {"ok": True})

        def log_message(self, fmt: str, *args: object) -> None:
            logging.debug(fmt, *args)

    return Handler


def main() -> None:
    """Serve on 127.0.0.1:<port>, writing events to <events_path>."""
    port, events_path = int(sys.argv[1]), sys.argv[2]
    ThreadingHTTPServer(("127.0.0.1", port), make_handler(events_path)).serve_forever()


if __name__ == "__main__":
    main()
