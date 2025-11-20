#!/bin/bash
set -e

echo "Initializing database by running trading system..."
python -m backend.src.main

echo "Starting API..."
exec uvicorn backend.src.api:app --host 0.0.0.0 --port 8000
