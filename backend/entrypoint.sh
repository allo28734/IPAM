#!/bin/bash
set -e

SECRETS_FILE="/app/data/app_secrets.env"

# 1. Generate secrets on the very first boot if they don't exist
if [ ! -f "$SECRETS_FILE" ]; then
    echo "First boot detected. Generating secure cryptographic keys..."
    mkdir -p /app/data
    
    JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
    FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    
    echo "export JWT_SECRET_KEY=$JWT_SECRET" > "$SECRETS_FILE"
    echo "export ENCRYPTION_KEY=$FERNET_KEY" >> "$SECRETS_FILE"
    echo "Secrets successfully generated and saved to persistent volume."
fi

# 2. Load the secrets into the environment
source "$SECRETS_FILE"

# 3. Apply database migrations
echo "Applying database migrations..."
alembic upgrade head

# 4. Start the application with Gunicorn (production process manager)
echo "Starting Gunicorn with Uvicorn workers..."
exec gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 4 \
    --bind 0.0.0.0:8000 \
    --graceful-timeout 30 \
    --access-logfile -
