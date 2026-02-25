"""
Stock4N – Lightweight REST API
Cho phép frontend (Next.js) trigger pipeline commands qua HTTP.
Chạy song song với Streamlit trong cùng container.
"""
import http.server
import json
import subprocess
import threading
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

PORT = 8502

# Whitelist commands for security
ALLOWED_COMMANDS = {
    "all":        "python src/main.py all",
    "ingestion":  "python src/main.py ingestion",
    "processing": "python src/main.py processing",
    "analysis":   "python src/main.py analysis",
    "portfolio":  "python src/main.py portfolio",
    "export":     "python src/main.py export",
    "breadth":    "python src/main.py breadth",
    "backtest":   "python src/main.py backtest",
    "learn":      "python src/main.py learn",
    "ml_train":   "python src/main.py ml_predict --ml-mode train",
    "ml_predict": "python src/main.py ml_predict --ml-mode predict",
    "adaptive":   "python src/main.py analysis --adaptive",
}


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

    # ── GET /health ─────────────────────────────────────
    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "ok"})
        elif self.path == "/commands":
            self._json(200, {"commands": list(ALLOWED_COMMANDS.keys())})
        else:
            self._json(404, {"error": "not found"})

    # ── POST /run/<command> ─────────────────────────────
    def do_POST(self):
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
