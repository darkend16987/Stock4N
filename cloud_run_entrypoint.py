"""
Cloud Run Entrypoint - Flask server for health checks and pipeline triggers.
Used when deploying to Google Cloud Run.
"""
import os
import subprocess
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all origins

# Whitelist commands for security (matching api_server.py)
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

@app.route('/health')
def health():
    """Health check endpoint for Cloud Run."""
    return jsonify({'status': 'ok', 'service': 'stock4n-pipeline'})

@app.route('/commands')
def get_commands():
    """Returns list of allowed commands."""
    return jsonify({'commands': list(ALLOWED_COMMANDS.keys())})

@app.route('/trigger', methods=['POST', 'GET'])
def trigger():
    """Compatibility trigger point (runs 'all')."""
    return run_cmd("all")

@app.route('/run/<command>', methods=['POST', 'GET'])
def run_cmd(command):
    """Run a specific pipeline command."""
    if command not in ALLOWED_COMMANDS:
        return jsonify({'error': f'Unknown command: {command}'}), 400

    cmd_string = ALLOWED_COMMANDS[command]
    logger.info(f"🚀 Running command: {cmd_string}")
    
    try:
        # Split command string for subprocess
        cmd_args = cmd_string.split()
        result = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=3600,
            cwd='/app'
        )
        
        success = result.returncode == 0
        logger.info(f"Command '{command}' finished with code {result.returncode}")
        
        return jsonify({
            'command': command,
            'success': success,
            'stdout': result.stdout[-3000:] if result.stdout else '',
            'stderr': result.stderr[-1000:] if result.stderr else ''
        }), 200 if success else 500

    except subprocess.TimeoutExpired:
        logger.error(f"❌ Command '{command}' timed out")
        return jsonify({'error': 'timeout', 'command': command}), 504
    except Exception as e:
        logger.error(f"❌ Internal error running '{command}': {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🌐 Starting Cloud Run server on port {port}")
    app.run(host='0.0.0.0', port=port)
