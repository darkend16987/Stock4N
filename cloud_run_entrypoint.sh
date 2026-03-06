#!/bin/bash
set -e

# Run the real API server
exec python src/api_server.py
