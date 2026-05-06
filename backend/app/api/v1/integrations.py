"""
Integrations API Router — Presentation Layer.

Thin router that handles HTTP concerns only:
  - Parse incoming requests via Pydantic schemas
  - Delegate to IntegrationService for business logic
  - Catch service-layer exceptions and map them to HTTP status codes
  - Return Pydantic response schemas

This router contains ZERO business logic or direct database access.
"""

from typing import List

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_admin, DbSession
from app.core.celery_app import celery_app
from app.core.database import get_db
from app.schemas.integration_provider import (
    ConnectionTestResponse,
    IntegrationProviderCreate,
    IntegrationProviderListResponse,
    IntegrationProviderResponse,
    IntegrationProviderUpdate,
    SyncResultResponse,
    VendorInfo,
)
from app.services.integration_service import (
    IntegrationService,
    IntegrationNotFoundError,
    IntegrationServiceError,
)
from app.worker.sync_tasks import sync_integration

router = APIRouter(
    prefix="/integrations",
    tags=["Integrations"],
    dependencies=[Depends(get_current_active_admin)],  # Admin-only
)


# ── Vendor metadata ────────────────────────────────────────────


@router.get("/vendors", response_model=List[VendorInfo])
async def list_supported_vendors():
    """List all supported vendor types and their configuration requirements."""
    return IntegrationService.get_supported_vendors()


# ── CRUD ───────────────────────────────────────────────────────


@router.post(
    "",
    response_model=IntegrationProviderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_integration(
    body: IntegrationProviderCreate,
    db: DbSession,
):
    """Create a new integration provider."""
    service = IntegrationService(db)
    try:
        provider = await service.create_provider(body)
        return IntegrationProviderResponse.model_validate(provider)
    except IntegrationServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=IntegrationProviderListResponse)
async def list_integrations(
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List all integration providers (API keys omitted)."""
    service = IntegrationService(db)
    items = await service.list_providers(skip=skip, limit=limit)
    total = await service.get_total_count()
    return IntegrationProviderListResponse(
        items=[IntegrationProviderResponse.model_validate(p) for p in items],
        total=total,
    )


@router.get("/{provider_id}", response_model=IntegrationProviderResponse)
async def get_integration(
    provider_id: int,
    db: DbSession,
):
    """Get a single integration provider by ID."""
    service = IntegrationService(db)
    try:
        provider = await service.get_provider(provider_id)
        return IntegrationProviderResponse.model_validate(provider)
    except IntegrationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{provider_id}", response_model=IntegrationProviderResponse)
async def update_integration(
    provider_id: int,
    body: IntegrationProviderUpdate,
    db: DbSession,
):
    """Update an integration provider's configuration."""
    service = IntegrationService(db)
    try:
        provider = await service.update_provider(provider_id, body)
        return IntegrationProviderResponse.model_validate(provider)
    except IntegrationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except IntegrationServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    provider_id: int,
    db: DbSession,
):
    """Delete an integration provider."""
    service = IntegrationService(db)
    try:
        await service.delete_provider(provider_id)
    except IntegrationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Connection test ────────────────────────────────────────────


@router.post(
    "/{provider_id}/test",
    response_model=ConnectionTestResponse,
)
async def test_integration_connection(
    provider_id: int,
    db: DbSession,
):
    """Test connectivity to the vendor API."""
    service = IntegrationService(db)
    try:
        result = await service.test_connection(provider_id)
        return ConnectionTestResponse(**result)
    except IntegrationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        return ConnectionTestResponse(ok=False, message=str(e))


# ── Manual sync ────────────────────────────────────────────────


@router.post("/{provider_id}/sync")
async def trigger_sync(
    provider_id: int,
    db: DbSession,
):
    """Trigger a background sync for a specific integration provider."""
    service = IntegrationService(db)
    try:
        await service.get_provider(provider_id)
    except IntegrationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    task = sync_integration.delay(provider_id)
    return {
        "task_id": task.id,
        "message": "Integration sync initiated in the background",
    }


@router.get("/sync/status/{task_id}")
def get_sync_status(task_id: str):
    """Check the status of a background integration sync Celery task."""
    result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": result.state,
        "result": result.result if result.ready() else None,
    }
