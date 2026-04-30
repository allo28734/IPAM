"""
Audit Log API router — Presentation Layer.

Read-only router for querying the audit trail.
"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession, get_current_user
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogListResponse, AuditLogResponse

from sqlalchemy import select, func

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    db: DbSession,
    entity_type: str | None = Query(None, max_length=50),
    action: str | None = Query(None, max_length=50),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Query audit log entries with optional filters.

    This endpoint is intentionally thin — the audit log has no
    complex business rules, so we query directly via SQLAlchemy
    rather than adding an unnecessary service layer.
    """
    stmt = select(AuditLog)

    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if action:
        stmt = stmt.where(AuditLog.action == action)

    # Count total before pagination
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0

    # Apply pagination and ordering (newest first)
    stmt = stmt.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit)
    items = db.scalars(stmt).all()

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in items],
        total=total,
    )
