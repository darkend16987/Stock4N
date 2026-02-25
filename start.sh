#!/bin/bash
set -e

echo "================================================"
echo "  Stock4N — Starting all services..."
echo "================================================"

# Start API server for frontend communication
echo "[Stock4N] Starting REST API server on port 8502..."
python /app/src/api_server.py &

# Start Streamlit dashboard
echo "[Stock4N] Starting Streamlit dashboard on port 8501..."
streamlit run /app/app_streamlit.py \
  --server.port 8501 \
  --server.headless true \
  --server.address 0.0.0.0 &

echo "================================================"
echo "  Stock4N — All services started!"
echo "  API Server:  http://localhost:8502"
echo "  Streamlit:   http://localhost:8501"
echo "  Frontend:    http://localhost:4000"
echo "================================================"

# Keep container alive
exec tail -f /dev/null
