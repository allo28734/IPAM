"""
Dashboard API router — Presentation Layer.

Provides aggregate statistics for the IPAM dashboard.
"""

from fastapi import APIRouter

from app.api.deps import IPServiceDep, SubnetServiceDep
from app.schemas.subnet import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    subnet_service: SubnetServiceDep,
    ip_service: IPServiceDep,
):
    """Return aggregate IPAM statistics for the dashboard."""
    total_subnets = subnet_service.get_total_count()
    total_ips = ip_service.get_total_count()
    assigned = ip_service.get_total_count_by_status("assigned")
    available = ip_service.get_total_count_by_status("available")
    reserved = ip_service.get_total_count_by_status("reserved")

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
