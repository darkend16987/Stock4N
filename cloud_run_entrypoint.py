"""
Cloud Run Entrypoint - Flask server for health checks and pipeline triggers.
Used when deploying to Google Cloud Run.
"""
import os
import subprocess
import logging
from flask import Flask, jsonify

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/health')
def health():
    """Health check endpoint for Cloud Run."""
    return jsonify({'status': 'healthy', 'service': 'stock4n-pipeline'})


@app.route('/trigger', methods=['POST', 'GET'])
def trigger():
    """Trigger the Stock4N pipeline."""
    logger.info("🚀 Pipeline triggered via HTTP request")
    try:
        result = subprocess.run(
            ['python', 'src/main.py', 'all'],
            capture_output=True,
            text=True,
            timeout=3600,
            cwd='/app'
        )
        logger.info(f"Pipeline stdout: {result.stdout[-500:] if result.stdout else 'N/A'}")
        if result.stderr:
            logger.warning(f"Pipeline stderr: {result.stderr[-500:]}")

        return jsonify({
            'status': 'completed' if result.returncode == 0 else 'error',
            'returncode': result.returncode,
            'stdout': result.stdout[-2000:] if result.stdout else '',
            'stderr': result.stderr[-2000:] if result.stderr else ''
        }), 200 if result.returncode == 0 else 500
    except subprocess.TimeoutExpired:
        logger.error("❌ Pipeline timed out after 3600s")
        return jsonify({'status': 'timeout', 'message': 'Pipeline exceeded 3600s timeout'}), 504
    except Exception as e:
        logger.error(f"❌ Pipeline error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🌐 Starting Cloud Run server on port {port}")
    app.run(host='0.0.0.0', port=port)
