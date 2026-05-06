"""
Pending Subnets API Router — Approval Queue.

Admin-only endpoints for reviewing, approving, and dismissing
subnets discovered by vendor integrations.
"""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_admin, DbSession
from app.models.pending_subnet import PendingSubnet
from app.models.subnet import Subnet
from app.schemas.pending_subnet import (
    ApproveSubnetRequest,
    PendingSubnetListResponse,
    PendingSubnetResponse,
)

router = APIRouter(
    prefix="/pending-subnets",
    tags=["Approval Queue"],
    dependencies=[Depends(get_current_active_admin)],  # Admin-only
)


# ── List pending subnets ───────────────────────────────────────


@router.get("", response_model=PendingSubnetListResponse)
async def list_pending_subnets(
    db: DbSession,
    status_filter: str = Query("pending", max_length=20, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """
    List pending subnets, optionally filtered by status.

    Defaults to showing only 'pending' items. Use status=all
    to include approved and dismissed items.
    """
    stmt = select(PendingSubnet).order_by(PendingSubnet.discovered_at.desc())

    if status_filter != "all":
        stmt = stmt.where(PendingSubnet.status == status_filter)

    stmt = stmt.offset(skip).limit(limit)
    result = await db.scalars(stmt)
    items = list(result.all())

    # Total count
    count_stmt = select(func.count(PendingSubnet.id))
    if status_filter != "all":
        count_stmt = count_stmt.where(PendingSubnet.status == status_filter)
    total = await db.scalar(count_stmt) or 0

    return PendingSubnetListResponse(
        items=[PendingSubnetResponse.model_validate(p) for p in items],
        total=total,
    )


# ── Get single pending subnet ─────────────────────────────────


@router.get("/count")
async def get_pending_count(db: DbSession):
    """Get the count of pending subnets (used for badge display)."""
    count = await db.scalar(
        select(func.count(PendingSubnet.id)).where(
            PendingSubnet.status == "pending"
        )
    )
    return {"count": count or 0}


@router.get("/{pending_id}", response_model=PendingSubnetResponse)
async def get_pending_subnet(
    pending_id: int,
    db: DbSession,
):
    """Get a single pending subnet by ID."""
    pending = await db.get(PendingSubnet, pending_id)
    if not pending:
        raise HTTPException(status_code=404, detail="Pending subnet not found")
    return PendingSubnetResponse.model_validate(pending)


# ── Approve ────────────────────────────────────────────────────


@router.post("/{pending_id}/approve", status_code=status.HTTP_201_CREATED)
async def approve_pending_subnet(
    pending_id: int,
    body: ApproveSubnetRequest,
    db: DbSession,
):
    """
    Approve a pending subnet — creates it in the subnets table.

    Optional overrides (name, description, parent_id) can be provided.
    """
    pending = await db.get(PendingSubnet, pending_id)
    if not pending:
        raise HTTPException(status_code=404, detail="Pending subnet not found")

    if pending.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Subnet already {pending.status}"
        )

    # Check that the CIDR doesn't already exist in subnets
    existing = (await db.scalars(
        select(Subnet).where(Subnet.cidr == pending.cidr)
    )).first()
    if existing:
        # Auto-dismiss since it already exists
        pending.status = "dismissed"
        pending.resolved_at = datetime.now(timezone.utc)
        await db.commit()
        raise HTTPException(
            status_code=409,
            detail=f"Subnet {pending.cidr} already exists (id={existing.id}). Entry dismissed."
        )

    # Create the subnet
    new_subnet = Subnet(
        name=body.name or pending.name or f"Discovered: {pending.cidr}",
        cidr=pending.cidr,
        gateway=pending.gateway,
        vlan_id=pending.vlan_id,
        ip_version=pending.ip_version,
        description=body.description or pending.description or f"Approved from {pending.vendor} integration",
        parent_id=body.parent_id,
    )
    db.add(new_subnet)

    # Mark as approved
    pending.status = "approved"
    pending.resolved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(new_subnet)

    return {
        "message": f"Subnet {pending.cidr} approved and created",
        "subnet_id": new_subnet.id,
    }


# ── Dismiss ────────────────────────────────────────────────────


@router.post("/{pending_id}/dismiss", status_code=status.HTTP_200_OK)
async def dismiss_pending_subnet(
    pending_id: int,
    db: DbSession,
):
    """Dismiss a pending subnet (ignore it without creating)."""
    pending = await db.get(PendingSubnet, pending_id)
    if not pending:
        raise HTTPException(status_code=404, detail="Pending subnet not found")

    if pending.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Subnet already {pending.status}"
        )

    pending.status = "dismissed"
    pending.resolved_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": f"Pending subnet {pending.cidr} dismissed"}


# ── Bulk actions ───────────────────────────────────────────────


@router.post("/bulk/approve", status_code=status.HTTP_200_OK)
async def bulk_approve(
    db: DbSession,
    ids: list[int] = Query(..., alias="id"),
):
    """Approve multiple pending subnets at once."""
    approved = 0
    errors = []

    for pid in ids:
        pending = await db.get(PendingSubnet, pid)
        if not pending or pending.status != "pending":
            errors.append(f"ID {pid}: not found or already resolved")
            continue

        # Check CIDR doesn't already exist
        existing = (await db.scalars(
            select(Subnet).where(Subnet.cidr == pending.cidr)
        )).first()
        if existing:
            pending.status = "dismissed"
            pending.resolved_at = datetime.now(timezone.utc)
            errors.append(f"ID {pid}: {pending.cidr} already exists, auto-dismissed")
            continue

        new_subnet = Subnet(
            name=pending.name or f"Discovered: {pending.cidr}",
            cidr=pending.cidr,
            gateway=pending.gateway,
            vlan_id=pending.vlan_id,
            ip_version=pending.ip_version,
            description=pending.description or f"Approved from {pending.vendor} integration",
        )
        db.add(new_subnet)
        pending.status = "approved"
        pending.resolved_at = datetime.now(timezone.utc)
        approved += 1

    await db.commit()
    return {"approved": approved, "errors": errors}


@router.post("/bulk/dismiss", status_code=status.HTTP_200_OK)
async def bulk_dismiss(
    db: DbSession,
    ids: list[int] = Query(..., alias="id"),
):
    """Dismiss multiple pending subnets at once."""
    dismissed = 0
    for pid in ids:
        pending = await db.get(PendingSubnet, pid)
        if pending and pending.status == "pending":
            pending.status = "dismissed"
            pending.resolved_at = datetime.now(timezone.utc)
            dismissed += 1

    await db.commit()
    return {"dismissed": dismissed}
