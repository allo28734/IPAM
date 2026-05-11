# IPAM Backend

This directory contains the core API, database models, background task workers, and multi-vendor integration adapters for the IPAM application. It is built using **FastAPI**, **SQLAlchemy 2.0 (async)**, and **Celery**.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Web Framework** | FastAPI |
| **ORM & Database** | SQLAlchemy 2.0 (async) with PostgreSQL (asyncpg) |
| **Migrations** | Alembic |
| **Background Tasks** | Celery with Redis |
| **Security** | OAuth2 with JWT, Role-Based Access Control (RBAC), bcrypt password hashing |
| **Encryption** | Fernet symmetric encryption (via `cryptography`) |
| **SSO** | OIDC via `authlib` (optional) |
| **Discovery** | ICMP ping, SNMPv3 (`pysnmp`), Nmap OS detection |
| **Integrations** | Cisco Meraki SDK, FortiGate REST, Aruba Central `pycentral`, PAN-OS XML |

## Project Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app factory and router registration
│   ├── core/
│   │   ├── config.py            # Pydantic-settings configuration (env vars)
│   │   ├── database.py          # Async engine, session factory, Base class
│   │   └── celery_app.py        # Celery instance and beat schedule
│   ├── api/
│   │   ├── deps.py              # Dependency injection (auth, services, DB session)
│   │   └── v1/                  # Versioned API routers (one per resource)
│   │       ├── auth.py          # Login, register, SSO/OIDC, setup-status
│   │       ├── subnets.py       # Subnet CRUD, CSV import/export, sweep
│   │       ├── ip_addresses.py  # IP CRUD, allocate, release, CSV import/export
│   │       ├── dashboard.py     # Aggregate statistics
│   │       ├── audit.py         # Read-only audit log queries
│   │       ├── system.py        # System settings and feature flags
│   │       ├── integrations.py  # Vendor integration CRUD, test, sync
│   │       ├── pending_subnets.py  # Approval queue for discovered subnets
│   │       └── discovery_profiles.py  # SNMPv3 credential profiles
│   ├── models/                  # SQLAlchemy ORM models (data layer only)
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── services/                # Business logic layer (validation, rules)
│   ├── repositories/            # Data access layer (SQL queries only)
│   ├── integrations/            # Vendor adapter plugins (abstract base + 4 vendors)
│   ├── utils/                   # Stateless utility functions (IP math, ping, SNMP)
│   └── worker/                  # Celery background tasks (sweep, import, sync)
├── alembic/                     # Database migration scripts
├── alembic.ini                  # Alembic configuration
├── tests/                       # Automated test suite
├── scripts/                     # Utility scripts
├── entrypoint.sh                # Docker entrypoint (secret gen, migrations, Gunicorn)
├── Dockerfile                   # Backend container build
└── requirements.txt             # Python dependencies
```

## Environment Variables

Key configuration loaded via `pydantic-settings` from the `.env` file:

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg driver) | Yes |
| `REDIS_URL` | Redis connection string for Celery broker/backend | Yes |
| `JWT_SECRET_KEY` | 64-character hex string for JWT signing | Yes |
| `ENCRYPTION_KEY` | Fernet key for encrypting SNMP/API credentials at rest | Yes |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins | No (defaults to empty — set for local dev) |
| `DEBUG` | Set to `true` for SQL echo logging — **never in production** | No |

## Local Development Setup

To run the backend locally without Docker:

1. **Prerequisites**: Ensure you have Python 3.10+ and a running PostgreSQL instance.
2. **Virtual Environment**:
   ```bash
   cd backend
   python -m venv venv

   # Activate (Windows)
   venv\Scripts\activate

   # Activate (Linux/Mac)
   source venv/bin/activate
   ```
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Environment Variables**:
   Run `init.ps1` (Windows) or `init.sh` (Linux/Mac) from the **root IPAM directory** to generate a `.env` file with all required secrets. For local development, also ensure `CORS_ORIGINS=http://localhost:5173` is set in `.env` (the init scripts do not set this by default since it is only needed for local dev).
5. **Start the API Server**:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   The API will be available at `http://localhost:8000`, and the interactive Swagger documentation will be at `http://localhost:8000/docs`.

## Running Tests

To run the automated test suite from within the `backend/` directory:
```bash
pytest tests -v
```
*Note: This requires a running PostgreSQL database configured for testing.*

## Database Migrations (Alembic)

When modifying SQLAlchemy models, you must generate and apply a database migration:

1. **Generate a new migration**:
   ```bash
   alembic revision --autogenerate -m "Describe your changes here"
   ```
2. **Apply migrations**:
   ```bash
   alembic upgrade head
   ```
   > **Note:** When deploying via Docker, the `entrypoint.sh` script automatically applies pending migrations on container startup.

> **Important:** The `alembic.ini` file contains a placeholder `sqlalchemy.url` value. This is **intentionally ignored** — the actual database URL is loaded from the application's `config.py` settings inside `alembic/env.py`. You do not need to edit `alembic.ini` to change the database connection.

## Background Workers (Celery)

IPAM uses Celery to perform background tasks such as network sweeps, CSV imports, and vendor integration syncs without blocking the main API event loop.

To run Celery locally (requires a running Redis instance):
```bash
# Start the worker
celery -A app.core.celery_app worker --loglevel=info

# Start the beat scheduler (for periodic tasks)
celery -A app.core.celery_app beat --loglevel=info
```

**Periodic tasks configured in Celery Beat:**

| Task | Schedule | Description |
|------|----------|-------------|
| `sweep_all_subnets` | Top of every hour | Dispatches ICMP ping sweeps for all subnets |
| `sync_all_integrations` | Every 30 minutes | Syncs all enabled vendor integrations |

## API Endpoints Overview

All endpoints are mounted under `/api/v1`. Authentication is via JWT Bearer token unless noted otherwise.

| Route | Method | Auth | Description |
|-------|--------|------|-------------|
| `/auth/setup-status` | GET | None | Check if first-run setup is needed |
| `/auth/token` | POST | None | Login with username/password → JWT |
| `/auth/register` | POST | Admin* | Create a new user account |
| `/auth/me` | GET | User | Get current user profile |
| `/auth/sso/enabled` | GET | None | Check if SSO is configured |
| `/auth/sso/login` | GET | None | Initiate OIDC login flow |
| `/auth/sso/callback` | GET | None | Handle OIDC provider callback |
| `/subnets` | GET | User | List subnets (paginated, searchable) |
| `/subnets` | POST | Admin | Create a new subnet |
| `/subnets/{id}` | GET | User | Get subnet detail |
| `/subnets/{id}` | PUT | Admin | Update subnet metadata |
| `/subnets/{id}` | DELETE | Admin | Delete subnet and all IPs |
| `/subnets/{id}/utilization` | GET | User | Get subnet utilization stats |
| `/subnets/{id}/sweep` | POST | Admin | Trigger background ICMP sweep |
| `/subnets/export` | GET | User | Export all subnets as CSV |
| `/subnets/import` | POST | Admin | Import subnets from CSV (background) |
| `/subnets/{id}/ips` | GET | User | List IPs in a subnet |
| `/subnets/{id}/ips` | POST | Admin | Assign a specific IP |
| `/subnets/{id}/ips/next-available` | POST | Admin | Auto-allocate next available IP |
| `/subnets/{id}/ips/export` | GET | User | Export IPs as CSV |
| `/subnets/{id}/ips/import` | POST | Admin | Import IPs from CSV (background) |
| `/ips/{id}` | PUT | Admin | Update IP metadata |
| `/ips/{id}` | DELETE | Admin | Hard-delete an IP record |
| `/ips/{id}/release` | POST | Admin | Release IP (set to available) |
| `/dashboard/stats` | GET | User | Aggregate IPAM statistics |
| `/audit` | GET | User | Query audit log entries |
| `/system/settings` | GET/PUT | Admin | Manage system-wide settings |
| `/system/features` | GET | None | Public feature flags |
| `/system/discovery-health` | GET | None | Check if discovery workers are online |
| `/integrations` | CRUD | Admin | Manage vendor integrations |
| `/integrations/{id}/test` | POST | Admin | Test vendor API connectivity |
| `/integrations/{id}/sync` | POST | Admin | Trigger background vendor sync |
| `/pending-subnets` | GET | Admin | List approval queue |
| `/pending-subnets/{id}/approve` | POST | Admin | Approve a discovered subnet |
| `/pending-subnets/{id}/dismiss` | POST | Admin | Dismiss a discovered subnet |
| `/discovery-profiles` | CRUD | Admin | Manage SNMPv3 credential profiles |
| `/health` | GET | None | Health check endpoint |

*\* Registration is open (no auth) during first-run setup only. After the first admin is created, it requires an admin JWT.*
