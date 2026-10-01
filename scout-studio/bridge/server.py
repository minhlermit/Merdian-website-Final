#!/usr/bin/env python3
"""Local-only bridge for the original Python/Claude Code Scout pipeline."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import threading

from export import CACHE, CORE, export

REPORT = Path(os.getenv("STS_REPORT_DIR", CACHE / "reports")) / "latest.html"
SCRIPT = CORE / ".claude/skills/stock-token-scout/scripts/run_cycle.sh"
process: subprocess.Popen | None = None
lock = threading.Lock()
log_path = CACHE / "studio-run.log"


class Handler(BaseHTTPRequestHandler):
    def json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/overview":
            try:
                self.json(200, export())
            except Exception as exc:
                self.json(500, {"error": str(exc)})
        elif self.path == "/api/status":
            self.json(200, {"running": process is not None and process.poll() is None,
                            "exitCode": process.poll() if process is not None else None,
                            "logTail": log_path.read_text(encoding="utf-8", errors="replace")[-1600:] if log_path.is_file() else ""})
        elif self.path == "/api/report":
            if not REPORT.is_file():
                self.json(404, {"error": "No report yet"})
                return
            body = REPORT.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.json(404, {"error": "Unknown endpoint"})

    def do_POST(self):
        global process
        if self.path != "/api/run":
            self.json(404, {"error": "Unknown endpoint"})
            return
        if self.headers.get("Origin") not in ("http://127.0.0.1:5173", "http://localhost:5173"):
            self.json(403, {"error": "Local studio origin required"})
            return
        with lock:
            if process is not None and process.poll() is None:
                self.json(409, {"error": "Scout is already running"})
                return
            if not SCRIPT.is_file():
                self.json(500, {"error": "Bundled research-core is missing"})
                return
            CACHE.mkdir(parents=True, exist_ok=True)
            log = open(log_path, "w", encoding="utf-8")
            try:
                process = subprocess.Popen(["bash", str(SCRIPT)], cwd=CORE,
                                           stdout=log, stderr=subprocess.STDOUT,
                                           env={**os.environ, "STS_PROJECT_DIR": str(CORE)}, start_new_session=True)
            finally:
                log.close()
        self.json(202, {"running": True, "message": "Scout cycle started. This can take 5–15 minutes when research is queued."})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8787), Handler)
    print("Scout bridge: http://127.0.0.1:8787", flush=True)
    server.serve_forever()
