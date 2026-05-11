#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# init.sh — One-time IPAM environment bootstrapping
#
# Generates cryptographically strong passwords and keys for the
# .env file so the user never has to invent their own secrets.
# Safe to re-run: exits cleanly if .env already exists.
# ─────────────────────────────────────────────────────────────────
set -e

ENV_FILE=".env"
EXAMPLE_FILE=".env.example"

# ── Guard: don't overwrite an existing .env ────────────────────
if [ -f "$ENV_FILE" ]; then
    echo "✅ .env already exists. Skipping initialization."
    echo "   To regenerate, delete .env and run this script again."
    exit 0
fi

if [ ! -f "$EXAMPLE_FILE" ]; then
    echo "❌ Error: $EXAMPLE_FILE not found. Run this script from the IPAM project root."
    exit 1
fi

echo "🔐 Bootstrapping .env from .env.example..."
cp "$EXAMPLE_FILE" "$ENV_FILE"

# ── Generate secrets ───────────────────────────────────────────
# Uses Python (available in most environments and required by the backend anyway)
generate_secret() {
    python3 -c "import secrets; print(secrets.token_urlsafe($1))" 2>/dev/null || \
    python  -c "import secrets; print(secrets.token_urlsafe($1))"
}

generate_hex() {
    python3 -c "import secrets; print(secrets.token_hex($1))" 2>/dev/null || \
    python  -c "import secrets; print(secrets.token_hex($1))"
}

generate_fernet() {
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || \
    python  -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
}

DB_PASS=$(generate_secret 24)
REDIS_PASS=$(generate_secret 16)
PGADMIN_PASS=$(generate_secret 16)
JWT_KEY=$(generate_hex 32)
FERNET_KEY=$(generate_fernet)

# ── Replace CHANGE_ME placeholders ─────────────────────────────
sed -i "s|DB_PASSWORD=CHANGE_ME|DB_PASSWORD=$DB_PASS|"           "$ENV_FILE"
sed -i "s|REDIS_PASSWORD=CHANGE_ME|REDIS_PASSWORD=$REDIS_PASS|" "$ENV_FILE"
sed -i "s|PGADMIN_PASSWORD=CHANGE_ME|PGADMIN_PASSWORD=$PGADMIN_PASS|" "$ENV_FILE"
sed -i "s|JWT_SECRET_KEY=CHANGE_ME|JWT_SECRET_KEY=$JWT_KEY|"     "$ENV_FILE"
sed -i "s|ENCRYPTION_KEY=CHANGE_ME|ENCRYPTION_KEY=$FERNET_KEY|"  "$ENV_FILE"

echo ""
echo "✅ .env initialized with secure random credentials."
echo ""
echo "   Generated values (save these if needed for external DB access):"
echo "   ─────────────────────────────────────────────────────"
echo "   DB_PASSWORD:      $DB_PASS"
echo "   REDIS_PASSWORD:   $REDIS_PASS"
echo "   PGADMIN_PASSWORD: $PGADMIN_PASS"
echo "   ─────────────────────────────────────────────────────"
echo ""
echo "   JWT_SECRET_KEY and ENCRYPTION_KEY have been set automatically."
echo "   You can view them in .env if needed."
echo ""
echo "🚀 Run 'docker compose up -d' to start IPAM."
echo "   (Add '--profile discovery' for background network scanning)"
echo ""
