"""
Stock4N – Lightweight REST API
Cho phép frontend (Next.js) trigger pipeline commands qua HTTP.
Chạy song song với Streamlit trong cùng container.

Endpoints:
  GET  /health            → {"status": "ok"}
  GET  /commands           → list of commands
  POST /run/<command>      → run pipeline command (sync, 10min timeout)
  POST /scan/start         → start price_filter scan in background
  GET  /scan/status        → poll scan progress
  GET  /scan/results       → get scan results (CSV → JSON)
  POST /scan/stop          → cancel running scan
"""
import http.server
import json
import subprocess
import threading
import sys
import os
import signal
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

PORT = int(os.environ.get("PORT", 8502))

# Whitelist commands for security
ALLOWED_COMMANDS = {
    "all":          "python src/main.py all",
    "ingestion":    "python src/main.py ingestion",
    "processing":   "python src/main.py processing",
    "analysis":     "python src/main.py analysis",
    "portfolio":    "python src/main.py portfolio",
    "export":       "python src/main.py export",
    "breadth":      "python src/main.py breadth",
    "backtest":     "python src/main.py backtest",
    "learn":        "python src/main.py learn",
    "ml_train":     "python src/main.py ml_predict --ml-mode train",
    "ml_predict":   "python src/main.py ml_predict --ml-mode predict",
    "adaptive":     "python src/main.py analysis --adaptive",
    "price_filter": "python src/main.py price_filter",
}

# ── Background scan state ──────────────────────────────
_scan_lock = threading.Lock()
_scan_process = None      # subprocess.Popen when running
_scan_status = "idle"     # idle | running | completed | error
_scan_started_at = None
_scan_error = ""


def _run_scan_background():
    """Run price_filter in a background subprocess."""
    global _scan_process, _scan_status, _scan_started_at, _scan_error

    with _scan_lock:
        _scan_status = "running"
        _scan_started_at = time.strftime("%Y-%m-%d %H:%M:%S")
        _scan_error = ""

    try:
        proc = subprocess.Popen(
            "python src/main.py price_filter",
            shell=True, cwd="/app",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        with _scan_lock:
            _scan_process = proc

        proc.wait()  # block this thread until done

        with _scan_lock:
            _scan_process = None
            if proc.returncode == 0:
                _scan_status = "completed"
            else:
                _scan_status = "error"
                _scan_error = (proc.stderr.read() or b"").decode()[-500:]

    except Exception as e:
        with _scan_lock:
            _scan_process = None
            _scan_status = "error"
            _scan_error = str(e)


def _get_scan_progress():
    """Read progress file written by PriceFilterScanner."""
    progress_file = "/app/data/price_filter_progress.json"
    if os.path.exists(progress_file):
        try:
            with open(progress_file, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _get_scan_results():
    """Read scan results CSV and return as list of dicts."""
    result_file = "/app/data/processed/price_filter_results.csv"
    if os.path.exists(result_file):
        try:
            import csv
            with open(result_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                return list(reader)
        except Exception:
            pass
    return []


class APIHandler(http.server.BaseHTTPRequestHandler):

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    # ── OPTIONS (CORS preflight) ────────────────────────
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    # ── GET ──────────────────────────────────────────────
    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "ok"})

        elif self.path == "/commands":
            self._json(200, {"commands": list(ALLOWED_COMMANDS.keys())})

        elif self.path == "/scan/status":
            progress = _get_scan_progress()
            with _scan_lock:
                resp = {
                    "status": _scan_status,
                    "started_at": _scan_started_at or "",
                    "error": _scan_error,
                }
            if progress:
                resp["processed"] = len(progress.get("processed_symbols", []))
                resp["batch"] = f"{progress.get('batch_idx', 0)}/{progress.get('total_batches', 0)}"
                resp["matches"] = progress.get("results_count", 0)
                resp["errors"] = progress.get("errors_count", 0)
                resp["last_update"] = progress.get("timestamp", "")
            self._json(200, resp)

        elif self.path == "/scan/results":
            results = _get_scan_results()
            self._json(200, {"count": len(results), "results": results})

        else:
            self._json(404, {"error": "not found"})

    # ── POST ─────────────────────────────────────────────
    def do_POST(self):
        global _scan_status
        # ── /scan/start ──
        if self.path == "/scan/start":
            with _scan_lock:
                if _scan_status == "running":
                    self._json(409, {"error": "scan already running"})
                    return

            t = threading.Thread(target=_run_scan_background, daemon=True)
            t.start()
            self._json(200, {"success": True, "message": "scan started"})
            return

        # ── /scan/stop ──
        if self.path == "/scan/stop":
            with _scan_lock:
                proc = _scan_process
            if proc and proc.poll() is None:
                proc.terminate()
                with _scan_lock:
                    _scan_status = "idle"
                self._json(200, {"success": True, "message": "scan stopped"})
            else:
                self._json(200, {"success": False, "message": "no scan running"})
            return

        # ── /run/<command> ──
        if not self.path.startswith("/run/"):
            self._json(404, {"error": "not found"})
            return

        cmd_key = self.path[5:]   # strip "/run/"
        if cmd_key not in ALLOWED_COMMANDS:
            self._json(400, {"error": f"unknown command: {cmd_key}",
                             "allowed": list(ALLOWED_COMMANDS.keys())})
            return

        cmd = ALLOWED_COMMANDS[cmd_key]

        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=600, cwd="/app"
            )
            self._json(200, {
                "command": cmd_key,
                "success": result.returncode == 0,
                "stdout":  result.stdout[-3000:],   # last 3000 chars
                "stderr":  result.stderr[-1000:] if result.returncode != 0 else "",
            })
        except subprocess.TimeoutExpired:
            self._json(504, {"error": "timeout", "command": cmd_key})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def log_message(self, fmt, *args):
        # quiet logging
        pass


def start_api():
    server = http.server.HTTPServer(("0.0.0.0", PORT), APIHandler)
    print(f"[API] Listening on :{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    start_api()
