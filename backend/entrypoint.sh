#!/bin/bash
set -e

# Apply database migrations
echo "Applying database migrations..."
alembic upgrade head

# Start the application
echo "Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
