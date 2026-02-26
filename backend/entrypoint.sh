#!/bin/bash
set -e

echo "Starting DefiSys API Server..."
exec uvicorn backend.src.api:app --host 0.0.0.0 --port 8000
