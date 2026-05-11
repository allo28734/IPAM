# ─────────────────────────────────────────────────────────────────
# init.ps1 — One-time IPAM environment bootstrapping (Windows)
#
# Generates cryptographically strong passwords and keys for the
# .env file so the user never has to invent their own secrets.
# Safe to re-run: exits cleanly if .env already exists.
# ─────────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"

$EnvFile = ".env"
$ExampleFile = ".env.example"

# ── Guard: don't overwrite an existing .env ────────────────────
if (Test-Path $EnvFile) {
    Write-Host "✅ .env already exists. Skipping initialization." -ForegroundColor Green
    Write-Host "   To regenerate, delete .env and run this script again." -ForegroundColor Gray
    exit 0
}

if (-not (Test-Path $ExampleFile)) {
    Write-Host "❌ Error: $ExampleFile not found. Run this script from the IPAM project root." -ForegroundColor Red
    exit 1
}

# ── Locate Python ──────────────────────────────────────────────
$PythonCmd = $null
foreach ($cmd in @("python", "python3")) {
    try {
        $null = & $cmd --version 2>&1
        $PythonCmd = $cmd
        break
    } catch { }
}

if (-not $PythonCmd) {
    Write-Host "❌ Error: Python is required but was not found on PATH." -ForegroundColor Red
    exit 1
}

Write-Host "🔐 Bootstrapping .env from .env.example..." -ForegroundColor Cyan

# ── Generate secrets using Python ──────────────────────────────
$DbPass      = & $PythonCmd -c "import secrets; print(secrets.token_urlsafe(24))"
$RedisPass   = & $PythonCmd -c "import secrets; print(secrets.token_urlsafe(16))"
$PgAdminPass = & $PythonCmd -c "import secrets; print(secrets.token_urlsafe(16))"
$JwtKey      = & $PythonCmd -c "import secrets; print(secrets.token_hex(32))"
$FernetKey   = & $PythonCmd -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# ── Read template and replace CHANGE_ME placeholders ───────────
$content = Get-Content $ExampleFile -Raw

$content = $content -replace "DB_PASSWORD=CHANGE_ME",      "DB_PASSWORD=$DbPass"
$content = $content -replace "REDIS_PASSWORD=CHANGE_ME",    "REDIS_PASSWORD=$RedisPass"
$content = $content -replace "PGADMIN_PASSWORD=CHANGE_ME",  "PGADMIN_PASSWORD=$PgAdminPass"
$content = $content -replace "JWT_SECRET_KEY=CHANGE_ME",    "JWT_SECRET_KEY=$JwtKey"
$content = $content -replace "ENCRYPTION_KEY=CHANGE_ME",    "ENCRYPTION_KEY=$FernetKey"

# Write with UTF-8 encoding (no BOM) for Docker compatibility
[System.IO.File]::WriteAllText((Resolve-Path -Path "." | Join-Path -ChildPath $EnvFile), $content, [System.Text.UTF8Encoding]::new($false))

Write-Host ""
Write-Host "✅ .env initialized with secure random credentials." -ForegroundColor Green
Write-Host ""
Write-Host "   Generated values (save these if needed for external DB access):" -ForegroundColor White
Write-Host "   ─────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "   DB_PASSWORD:      $DbPass" -ForegroundColor Yellow
Write-Host "   REDIS_PASSWORD:   $RedisPass" -ForegroundColor Yellow
Write-Host "   PGADMIN_PASSWORD: $PgAdminPass" -ForegroundColor Yellow
Write-Host "   ─────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""
Write-Host "   JWT_SECRET_KEY and ENCRYPTION_KEY have been set automatically." -ForegroundColor Gray
Write-Host "   You can view them in .env if needed." -ForegroundColor Gray
Write-Host ""
Write-Host "🚀 Run 'docker compose up -d' to start IPAM." -ForegroundColor Cyan
Write-Host "   (Add '--profile discovery' for background network scanning)" -ForegroundColor Gray
Write-Host ""
