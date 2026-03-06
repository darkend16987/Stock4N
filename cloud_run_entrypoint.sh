#!/bin/bash
set -e

# If PORT is set, run as web server
if [ ! -z "$PORT" ]; then
    # Run Flask server for health checks and manual triggers
    python -c "
from flask import Flask, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/trigger', methods=['POST', 'GET'])
def trigger():
    try:
        result = subprocess.run(['python', 'src/main.py', 'all'],
                              capture_output=True, text=True, timeout=3600)
        return jsonify({
            'status': 'completed',
            'stdout': result.stdout,
            'stderr': result.stderr
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
"
else
    # Run pipeline directly
    python src/main.py all
fi
