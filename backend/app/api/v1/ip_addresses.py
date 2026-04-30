"""
IP Address API router — Presentation Layer.

Thin router for IP address CRUD and allocation operations.
Delegates all business logic to IPAddressService.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Response

from app.api.deps import IPServiceDep, SubnetServiceDep, get_current_user
from app.schemas.ip_address import (
    IPAddressAllocate,
    IPAddressCreate,
    IPAddressListResponse,
    IPAddressResponse,
    IPAddressUpdate,
)
from app.services.ip_address_service import (
    IPConflictError,
    IPNotFoundError,
    IPValidationError,
    SubnetFullError,
    SubnetNotFoundError,
)

router = APIRouter(
    tags=["ip-addresses"],
    dependencies=[Depends(get_current_user)],
)


# ── List IPs in a subnet ───────────────────────────────────────


@router.get(
    "/subnets/{subnet_id}/ips",
    response_model=IPAddressListResponse,
)
def list_ips_in_subnet(
    subnet_id: int,
    service: IPServiceDep,
    status_filter: str | None = Query(None, alias="status", max_length=20),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List all IP addresses in a subnet with optional status filter."""
    try:
        items = service.list_ips_in_subnet(
            subnet_id, status=status_filter, skip=skip, limit=limit
        )
    except SubnetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except IPValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return IPAddressListResponse(
        items=[IPAddressResponse.model_validate(ip) for ip in items],
        total=len(items),
    )


# ── Bulk Operations ─────────────────────────────────────────────


@router.get("/subnets/{subnet_id}/ips/export", response_class=Response)
def export_ips(subnet_id: int, service: IPServiceDep):
    """Export all IPs in a subnet as CSV."""
    try:
        csv_data = service.export_csv(subnet_id)
    except SubnetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
        
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=subnet_{subnet_id}_ips.csv"}
    )


@router.post("/subnets/{subnet_id}/ips/import")
async def import_ips(subnet_id: int, service: IPServiceDep, file: UploadFile = File(...)):
    """Import IP addresses from a CSV file."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
        
    content = await file.read()
    try:
        csv_str = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid file encoding. Must be UTF-8")
        
    result = service.bulk_import(subnet_id, csv_str)
    return result


# ── Assign a specific IP ───────────────────────────────────────


@router.post(
    "/subnets/{subnet_id}/ips",
    response_model=IPAddressResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_ip(subnet_id: int, body: IPAddressCreate, service: IPServiceDep):
    """Assign or reserve a specific IP address in a subnet."""
    try:
        ip = service.assign_ip(
            subnet_id,
            address=body.address,
            status=body.status,
            hostname=body.hostname,
            description=body.description,
            tags=body.tags,
        )
    except SubnetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except IPValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except IPConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return IPAddressResponse.model_validate(ip)


# ── Auto-allocate next available ────────────────────────────────


@router.post(
    "/subnets/{subnet_id}/ips/next-available",
    response_model=IPAddressResponse,
    status_code=status.HTTP_201_CREATED,
)
def allocate_next_available(
    subnet_id: int, body: IPAddressAllocate, service: IPServiceDep
):
    """Automatically allocate the next available IP in a subnet."""
    try:
        ip = service.allocate_next_available(
            subnet_id,
            status=body.status,
            hostname=body.hostname,
            description=body.description,
            tags=body.tags,
        )
    except SubnetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except IPValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except SubnetFullError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return IPAddressResponse.model_validate(ip)


# ── Update IP ───────────────────────────────────────────────────


@router.put("/ips/{ip_id}", response_model=IPAddressResponse)
def update_ip(ip_id: int, body: IPAddressUpdate, service: IPServiceDep):
    """Update IP address metadata (status, hostname, description)."""
    try:
        ip = service.update_ip(
            ip_id,
            status=body.status,
            hostname=body.hostname,
            description=body.description,
            tags=body.tags,
        )
    except IPNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except IPValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return IPAddressResponse.model_validate(ip)


# ── Release IP (soft delete) ───────────────────────────────────


@router.post("/ips/{ip_id}/release", response_model=IPAddressResponse)
def release_ip(ip_id: int, service: IPServiceDep):
    """Release an IP address (set status to 'available', clear hostname)."""
    try:
        ip = service.release_ip(ip_id)
    except IPNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return IPAddressResponse.model_validate(ip)


# ── Delete IP (hard delete) ────────────────────────────────────


@router.delete("/ips/{ip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ip(ip_id: int, service: IPServiceDep):
    """Permanently remove an IP address record."""
    try:
        service.delete_ip(ip_id)
    except IPNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
