#!/usr/bin/env python3
"""
FreelanceMCP Web Dashboard Server
----------------------------------
Serves the Vue 3 dashboard and provides a minimal REST API that bridges
the dashboard to search_gigs.py (headless mode).

Usage:
    python web_ui.py                  # default port 8080
    WEBUI_PORT=9000 python web_ui.py
    APP_ENV=dev python web_ui.py      # passes APP_ENV to the child process
"""

import json
import os
import signal
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
BIDS_FILE   = Path(os.getenv("BIDS_JSON_PATH",   "bids.json"))
STATUS_FILE = Path(os.getenv("STATUS_JSON_PATH", "status.json"))
DASHBOARD   = Path(__file__).parent / "dashboard" / "index.html"

# ── Subprocess state (protected by a lock) ────────────────────────────────
_lock    = threading.Lock()
_proc: subprocess.Popen | None = None


def _proc_running() -> bool:
    """Return True if the child process is alive."""
    with _lock:
        if _proc is None:
            return False
        return _proc.poll() is None


def _start_process() -> dict:
    global _proc
    with _lock:
        if _proc is not None and _proc.poll() is None:
            return {"ok": False, "error": "Already running", "pid": _proc.pid}

        env = os.environ.copy()
        cmd = [sys.executable, "search_gigs.py", "--headless"]
        try:
            _proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    return {"ok": True, "pid": _proc.pid}


def _stop_process() -> dict:
    global _proc
    with _lock:
        if _proc is None or _proc.poll() is not None:
            return {"ok": False, "error": "Not running"}
        try:
            os.kill(_proc.pid, signal.SIGTERM)
            _proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _proc.kill()
        except ProcessLookupError:
            pass
        _proc = None

    # Mark status file immediately so the dashboard updates fast
    try:
        STATUS_FILE.write_text(
            json.dumps({"running": False, "pid": None,
                        "updated_at": datetime.now().isoformat()}),
            encoding="utf-8",
        )
    except Exception:
        pass

    return {"ok": True}


def _read_bids() -> list:
    try:
        if BIDS_FILE.exists():
            data = json.loads(BIDS_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []


def _clear_bids() -> None:
    try:
        BIDS_FILE.write_text("[]", encoding="utf-8")
    except Exception:
        pass


def _read_status() -> dict:
    # Prefer live process state over the file
    running = _proc_running()
    pid     = None
    with _lock:
        if _proc is not None and _proc.poll() is None:
            pid = _proc.pid

    # If our in-memory state says not running, also check status.json
    # (in case search_gigs.py was started independently)
    if not running and STATUS_FILE.exists():
        try:
            data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                file_running = data.get("running", False)
                file_pid     = data.get("pid")
                # Verify the PID is actually alive
                if file_running and file_pid:
                    try:
                        os.kill(file_pid, 0)  # signal 0 = existence check
                        running = True
                        pid     = file_pid
                    except (ProcessLookupError, PermissionError):
                        running = False
        except Exception:
            pass

    return {"running": running, "pid": pid, "updated_at": datetime.now().isoformat()}


# ── HTTP handler ──────────────────────────────────────────────────────────

CORS_HEADERS = {
    "Access-Control-Allow-Origin":  "*",
    "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


class DashboardHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler — no external dependencies required."""

    # Suppress default request log to stderr; replace with clean output
    def log_message(self, fmt, *args):  # noqa: N802
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.command} {self.path} — {args[1]}")

    # ── Routing ────────────────────────────────────────────────────────────

    def do_OPTIONS(self):  # noqa: N802
        self._send(204, b"", content_type="text/plain")

    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]
        if path == "/" or path == "/index.html":
            self._serve_dashboard()
        elif path == "/api/bids":
            self._json_response(_read_bids())
        elif path == "/api/status":
            self._json_response(_read_status())
        else:
            self._send(404, b"Not found")

    def do_POST(self):  # noqa: N802
        path = self.path.split("?")[0]
        if path == "/api/start":
            result = _start_process()
            code = 200 if result.get("ok") else 409
            self._json_response(result, code)
        elif path == "/api/stop":
            result = _stop_process()
            code = 200 if result.get("ok") else 409
            self._json_response(result, code)
        else:
            self._send(404, b"Not found")

    def do_DELETE(self):  # noqa: N802
        if self.path.split("?")[0] == "/api/bids":
            _clear_bids()
            self._json_response({"ok": True})
        else:
            self._send(404, b"Not found")

    # ── Helpers ────────────────────────────────────────────────────────────

    def _serve_dashboard(self):
        if not DASHBOARD.exists():
            self._send(
                503,
                b"dashboard/index.html not found. "
                b"Make sure the dashboard/ directory exists.",
            )
            return
        html = DASHBOARD.read_bytes()
        self._send(200, html, content_type="text/html; charset=utf-8")

    def _json_response(self, data: object, code: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._send(code, body, content_type="application/json; charset=utf-8")

    def _send(self, code: int, body: bytes, content_type: str = "text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)


# ── Entry point ──────────────────────────────────────────────────────────

def main() -> None:
    port = int(os.getenv("WEBUI_PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)

    print("═" * 56)
    print("  FreelanceMCP Dashboard")
    print(f"  http://localhost:{port}")
    print("═" * 56)
    print("  Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down…")
        # Stop child process if running
        _stop_process()
        server.server_close()


if __name__ == "__main__":
    main()
