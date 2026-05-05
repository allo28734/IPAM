#!/bin/bash
set -e

# Apply database migrations
echo "Applying database migrations..."
alembic upgrade head

# Start the application with Gunicorn (production process manager)
# - UvicornWorker: ASGI worker class for FastAPI
# - 4 workers: handles concurrent requests across multiple processes
# - graceful-timeout: allows workers to finish in-flight requests
echo "Starting Gunicorn with Uvicorn workers..."
exec gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 4 \
    --bind 0.0.0.0:8000 \
    --graceful-timeout 30 \
    --access-logfile -
