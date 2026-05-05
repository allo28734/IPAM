"""
Subnet API router — Presentation Layer.

Thin router that handles HTTP concerns only:
  - Parse incoming requests via Pydantic schemas
  - Delegate to SubnetService for business logic
  - Catch service-layer exceptions and map them to HTTP status codes
  - Return Pydantic response schemas

This router contains ZERO business logic or direct database access.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Response
import ipaddress
from celery.result import AsyncResult
from app.core.celery_app import celery_app
from app.worker.sweep_tasks import run_subnet_sweep

from app.api.deps import IPServiceDep, SubnetServiceDep, get_current_user, get_current_active_admin
from app.schemas.ip_address import IPAddressResponse
from app.schemas.subnet import (
    DashboardStats,
    SubnetCreate,
    SubnetListResponse,
    SubnetResponse,
    SubnetUpdate,
    SubnetUtilization,
)
from app.services.subnet_service import (
    SubnetConflictError,
    SubnetNotFoundError,
    SubnetValidationError,
)

router = APIRouter(
    prefix="/subnets",
    tags=["subnets"],
    dependencies=[Depends(get_current_user)],
)


# ── List subnets ────────────────────────────────────────────────


@router.get("", response_model=SubnetListResponse)
def list_subnets(
    service: SubnetServiceDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: str | None = Query(None, max_length=255),
):
    """List all subnets with optional search and pagination."""
    items = service.list_subnets(skip=skip, limit=limit, search=search)
    total = service.get_total_count()
    return SubnetListResponse(
        items=[SubnetResponse.model_validate(s) for s in items],
        total=total,
    )


# ── Bulk Operations ─────────────────────────────────────────────


@router.get("/export", response_class=Response)
def export_subnets(service: SubnetServiceDep):
    """Export all subnets as CSV."""
    csv_data = service.export_csv()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=subnets.csv"}
    )


@router.post("/import", dependencies=[Depends(get_current_active_admin)])
async def import_subnets(service: SubnetServiceDep, file: UploadFile = File(...)):
    """Import subnets from a CSV file."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
        
    if file.size is not None and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File size exceeds 5MB limit")
        
    import codecs
    iterator = codecs.iterdecode(file.file, 'utf-8-sig')
    result = service.bulk_import(iterator)
    return result


# ── Create subnet ──────────────────────────────────────────────


@router.post("", response_model=SubnetResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_active_admin)])
def create_subnet(body: SubnetCreate, service: SubnetServiceDep):
    """Create a new subnet."""
    try:
        subnet = service.create_subnet(
            name=body.name,
            cidr=body.cidr,
            gateway=body.gateway,
            vlan_id=body.vlan_id,
            description=body.description,
            parent_id=body.parent_id,
            tags=body.tags,
        )
    except SubnetValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except SubnetConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return SubnetResponse.model_validate(subnet)


# ── Get subnet detail ──────────────────────────────────────────


@router.get("/{subnet_id}", response_model=SubnetResponse)
def get_subnet(subnet_id: int, service: SubnetServiceDep):
    """Get a single subnet by ID."""
    try:
        subnet = service.get_subnet(subnet_id)
    except SubnetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return SubnetResponse.model_validate(subnet)


# ── Update subnet ──────────────────────────────────────────────


@router.put("/{subnet_id}", response_model=SubnetResponse, dependencies=[Depends(get_current_active_admin)])
def update_subnet(subnet_id: int, body: SubnetUpdate, service: SubnetServiceDep):
    """Update subnet metadata (name, gateway, vlan, description)."""
    try:
        subnet = service.update_subnet(
            subnet_id,
            name=body.name,
            gateway=body.gateway,
            vlan_id=body.vlan_id,
            description=body.description,
            parent_id=body.parent_id,
            tags=body.tags,
        )
    except SubnetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except SubnetValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return SubnetResponse.model_validate(subnet)


# ── Delete subnet ──────────────────────────────────────────────


@router.delete("/{subnet_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_active_admin)])
def delete_subnet(subnet_id: int, service: SubnetServiceDep):
    """Delete a subnet and all its associated IP addresses."""
    try:
        service.delete_subnet(subnet_id)
    except SubnetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ── Utilization ─────────────────────────────────────────────────


@router.get("/{subnet_id}/utilization", response_model=SubnetUtilization)
def get_utilization(subnet_id: int, service: SubnetServiceDep):
    """Get utilization statistics for a subnet."""
    try:
        stats = service.get_utilization(subnet_id)
    except SubnetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return SubnetUtilization(**stats)


# ── ICMP Sweep ──────────────────────────────────────────────────


@router.post("/{subnet_id}/sweep", dependencies=[Depends(get_current_active_admin)])
async def sweep_subnet_endpoint(subnet_id: int, service: SubnetServiceDep):
    """Trigger a background ICMP ping sweep for a subnet using Celery."""
    try:
        subnet = service.get_subnet(subnet_id)
    except SubnetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
        
    network = ipaddress.IPv4Network(subnet.cidr, strict=False)
    if network.num_addresses > 2048:
        raise HTTPException(
            status_code=400, 
            detail="Subnet too large for manual sweep. Please limit to /21 or smaller."
        )
        
    task = run_subnet_sweep.delay(subnet_id)
    return {"task_id": task.id, "message": "Sweep initiated in the background"}


@router.get("/sweep/status/{task_id}")
def get_sweep_status(task_id: str):
    """Check the status of a background ICMP sweep Celery task."""
    result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": result.state,
        "result": result.result if result.ready() else None
    }
