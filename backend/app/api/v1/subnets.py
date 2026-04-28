"""
Subnet API router — Presentation Layer.

Thin router that handles HTTP concerns only:
  - Parse incoming requests via Pydantic schemas
  - Delegate to SubnetService for business logic
  - Catch service-layer exceptions and map them to HTTP status codes
  - Return Pydantic response schemas

This router contains ZERO business logic or direct database access.
"""

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import IPServiceDep, SubnetServiceDep
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

router = APIRouter(prefix="/subnets", tags=["subnets"])


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


# ── Create subnet ──────────────────────────────────────────────


@router.post("", response_model=SubnetResponse, status_code=status.HTTP_201_CREATED)
def create_subnet(body: SubnetCreate, service: SubnetServiceDep):
    """Create a new subnet."""
    try:
        subnet = service.create_subnet(
            name=body.name,
            cidr=body.cidr,
            gateway=body.gateway,
            vlan_id=body.vlan_id,
            description=body.description,
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


@router.put("/{subnet_id}", response_model=SubnetResponse)
def update_subnet(subnet_id: int, body: SubnetUpdate, service: SubnetServiceDep):
    """Update subnet metadata (name, gateway, vlan, description)."""
    try:
        subnet = service.update_subnet(
            subnet_id,
            name=body.name,
            gateway=body.gateway,
            vlan_id=body.vlan_id,
            description=body.description,
        )
    except SubnetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except SubnetValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return SubnetResponse.model_validate(subnet)


# ── Delete subnet ──────────────────────────────────────────────


@router.delete("/{subnet_id}", status_code=status.HTTP_204_NO_CONTENT)
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
