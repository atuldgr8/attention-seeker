#!/usr/bin/env python3
"""Attention Seeker — places a REAL phone call via Twilio."""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
PORT = int(os.environ.get("PORT", "5173"))


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_env(ENV_PATH)

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "").strip()

E164 = re.compile(r"^\+[1-9]\d{7,14}$")


def twilio_configured() -> bool:
    return bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER)


def place_call(to_number: str) -> dict:
    if not twilio_configured():
        raise RuntimeError(
            "Twilio is not configured. Copy .env.example to .env and add your credentials."
        )
    if not E164.match(to_number):
        raise ValueError("Phone must be E.164 like +919876543210")

    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{TWILIO_ACCOUNT_SID}/Calls.json"
    )
    # Ring the handset for real. After answer, stay quiet so it feels like a normal call.
    twiml = (
        '<Response>'
        '<Pause length="60"/>'
        '<Say voice="alice">Okay, you have their attention. You can hang up.</Say>'
        "</Response>"
    )
    body = urllib.parse.urlencode(
        {
            "To": to_number,
            "From": TWILIO_FROM_NUMBER,
            "Twiml": twiml,
            "Timeout": "30",
        }
    ).encode("utf-8")

    req = urllib.request.Request(url, data=body, method="POST")
    token = base64.b64encode(
        f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}".encode("utf-8")
    ).decode("ascii")
    req.add_header("Authorization", f"Basic {token}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(detail)
            message = parsed.get("message") or detail
        except json.JSONDecodeError:
            message = detail or str(exc)
        raise RuntimeError(message) from exc

    return {
        "sid": payload.get("sid"),
        "status": payload.get("status"),
        "to": payload.get("to"),
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0] == "/api/health":
            self._json(
                200,
                {
                    "ok": True,
                    "twilioConfigured": twilio_configured(),
                    "from": TWILIO_FROM_NUMBER[-4:].rjust(len(TWILIO_FROM_NUMBER), "*")
                    if TWILIO_FROM_NUMBER
                    else None,
                },
            )
            return
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0] != "/api/call":
            self._json(404, {"error": "Not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "Invalid JSON"})
            return

        to_number = str(data.get("to", "")).strip()
        try:
            result = place_call(to_number)
        except ValueError as exc:
            self._json(400, {"error": str(exc)})
            return
        except RuntimeError as exc:
            self._json(500, {"error": str(exc)})
            return

        self._json(200, {"ok": True, **result})

    def log_message(self, fmt: str, *args) -> None:
        print(f"[server] {self.address_string()} - {fmt % args}")


def main() -> None:
    # Prefer this server over a bare static http.server so /api/call works.
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Attention Seeker real-call server on http://127.0.0.1:{PORT}")
    print(
        "Twilio:"
        + (" configured" if twilio_configured() else " NOT configured — fill in .env")
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")


if __name__ == "__main__":
    main()
