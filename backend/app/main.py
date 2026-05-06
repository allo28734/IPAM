"""
FastAPI application factory.

Creates the app instance, configures CORS middleware, and sets up
the database tables on startup via lifespan events.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.database import Base, engine

# Import all models so Base.metadata.create_all discovers every table
import app.models  # noqa: F401

# Import v1 routers
from app.api.v1 import audit as audit_router
from app.api.v1 import auth as auth_router
from app.api.v1 import dashboard as dashboard_router
from app.api.v1 import ip_addresses as ip_router
from app.api.v1 import subnets as subnet_router
from app.api.v1 import discovery_profiles as discovery_profile_router
from app.api.v1 import integrations as integrations_router
from app.api.v1 import pending_subnets as pending_subnets_router
from app.api.v1 import system as system_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events (e.g. startup/shutdown tasks)."""
    # Note: Table creation is now handled exclusively via Alembic migrations.
    yield


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        lifespan=lifespan,
    )

    # Session middleware — required by authlib for OIDC state storage
    app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret_key)

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
    app.include_router(auth_router.router, prefix=api_prefix)
    app.include_router(subnet_router.router, prefix=api_prefix)
    app.include_router(ip_router.router, prefix=api_prefix)
    app.include_router(audit_router.router, prefix=api_prefix)
    app.include_router(dashboard_router.router, prefix=api_prefix)
    app.include_router(discovery_profile_router.router, prefix=api_prefix)
    app.include_router(integrations_router.router, prefix=api_prefix)
    app.include_router(pending_subnets_router.router, prefix=api_prefix)
    app.include_router(system_router.router, prefix=api_prefix)

    # Health-check endpoint
    @app.get("/health", tags=["system"])
    def health_check():
        return {"status": "healthy", "version": settings.app_version}

    return app


app = create_app()
