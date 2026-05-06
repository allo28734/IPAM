"""
Dashboard API router — Presentation Layer.

Provides aggregate statistics for the IPAM dashboard.
"""

from fastapi import APIRouter, Depends

from app.api.deps import IPServiceDep, SubnetServiceDep, get_current_user
from app.schemas.subnet import DashboardStats

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    subnet_service: SubnetServiceDep,
    ip_service: IPServiceDep,
):
    """Return aggregate IPAM statistics for the dashboard."""
    total_subnets = await subnet_service.get_total_count()
    total_ips = await ip_service.get_total_count()
    assigned = await ip_service.get_total_count_by_status("assigned")
    available = await ip_service.get_total_count_by_status("available")
    reserved = await ip_service.get_total_count_by_status("reserved")

    # Overall utilization: assigned / (assigned + available + reserved)
    if total_ips > 0:
        utilization = round((assigned / total_ips) * 100, 2)
    else:
        utilization = 0.0

    return DashboardStats(
        total_subnets=total_subnets,
        total_ips=total_ips,
        assigned_ips=assigned,
        available_ips=available,
        reserved_ips=reserved,
        overall_utilization=utilization,
    )
