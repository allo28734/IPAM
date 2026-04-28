"""
FastAPI application factory.

Creates the app instance, configures CORS middleware, and sets up
the database tables on startup via lifespan events.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine

# Import all models so Base.metadata.create_all discovers every table
import app.models  # noqa: F401

# Import v1 routers
from app.api.v1 import audit as audit_router
from app.api.v1 import dashboard as dashboard_router
from app.api.v1 import ip_addresses as ip_router
from app.api.v1 import subnets as subnet_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup (MVP convenience — Alembic for prod)."""
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        lifespan=lifespan,
    )

    # CORS — allow the React dev server to call the API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount v1 API routers under /api/v1
    api_prefix = "/api/v1"
    app.include_router(subnet_router.router, prefix=api_prefix)
    app.include_router(ip_router.router, prefix=api_prefix)
    app.include_router(audit_router.router, prefix=api_prefix)
    app.include_router(dashboard_router.router, prefix=api_prefix)

    # Health-check endpoint
    @app.get("/health", tags=["system"])
    def health_check():
        return {"status": "healthy", "version": settings.app_version}

    return app


app = create_app()
