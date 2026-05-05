# IPAM Backend

This directory contains the core API, database models, and background task workers for the IPAM application. It is built using **FastAPI**, **SQLAlchemy**, and **Celery**.

## Tech Stack
- **Web Framework**: FastAPI
- **ORM & Database**: SQLAlchemy with PostgreSQL
- **Migrations**: Alembic
- **Background Tasks**: Celery with Redis
- **Security**: OAuth2 with JWT, Role-Based Access Control (RBAC)

## Local Development Setup

To run the backend locally without Docker:

1. **Prerequisites**: Ensure you have Python 3.10+ installed.
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
   Ensure you have a `.env` file in the root IPAM directory or export the required variables (`DATABASE_URL`, `JWT_SECRET_KEY`, etc.) manually.
5. **Start the API Server**:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   The API will be available at `http://localhost:8000`, and the interactive Swagger documentation will be at `http://localhost:8000/docs`.

## Database Migrations (Alembic)

When modifying SQLAlchemy models, you must generate and apply a database migration:

1. **Generate a new migration**:
   ```bash
   alembic revision --autogenerate -m "Describe your changes here"
   ```
2. **Apply migrations**:
   *Note: When deploying via Docker, the entrypoint script automatically applies pending migrations.*
   To apply manually:
   ```bash
   alembic upgrade head
   ```

## Background Workers (Celery)

IPAM uses Celery to perform background tasks such as network sweeps and ping checks without blocking the main API thread.

To run Celery locally (requires Redis):
```bash
# Start the worker
celery -A app.core.celery_app worker --loglevel=info

# Start the beat scheduler (for periodic tasks)
celery -A app.core.celery_app beat --loglevel=info
```
