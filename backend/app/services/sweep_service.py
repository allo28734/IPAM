"""
Sweep service — Background tasks for network verification.
"""

import logging
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models.ip_address import IPAddress
from app.models.subnet import Subnet
from app.repositories.ip_address_repo import IPAddressRepository
from app.repositories.subnet_repo import SubnetRepository
from app.services.ip_address_service import IPAddressService
from app.utils.ip_utils import get_usable_host_range
from app.utils.ping_utils import ping_sweep

logger = logging.getLogger(__name__)

async def run_subnet_sweep(subnet_id: int):
    """
    Background task to ping sweep a specific subnet.
    """
    db = SessionLocal()
    try:
        subnet = db.query(Subnet).filter(Subnet.id == subnet_id).first()
        if not subnet:
            logger.error(f"Sweep failed: Subnet {subnet_id} not found.")
            return

        usable_ips = get_usable_host_range(subnet.cidr)
        if not usable_ips:
            return

        # Sanity check limit (though API route should have enforced this)
        if len(usable_ips) > 2048:
            logger.warning(f"Subnet {subnet.cidr} exceeds 2048 IPs, capping sweep.")
            usable_ips = usable_ips[:2048]

        logger.info(f"Starting ICMP sweep of {len(usable_ips)} IPs in subnet {subnet.name} ({subnet.cidr})")
        results = await ping_sweep(usable_ips, max_concurrency=50)

        # Build service for auditing and creating IPs
        ip_service = IPAddressService(db)

        # Fetch existing IPs from the DB
        existing_ips_query = db.query(IPAddress).filter(IPAddress.subnet_id == subnet.id).all()
        existing_ips_map = {ip.address: ip for ip in existing_ips_query}

        conflict_count = 0
        updated_count = 0

        for ip_str, is_alive in results.items():
            if is_alive:
                if ip_str in existing_ips_map:
                    existing_ip = existing_ips_map[ip_str]
                    existing_ip.last_seen = datetime.now(timezone.utc)
                    updated_count += 1
                    
                    if existing_ip.status == "available":
                        existing_ip.status = "conflict"
                        conflict_count += 1
                        ip_service._log_audit("IPAddress", existing_ip.id, "sweep_conflict", {"address": ip_str})
                else:
                    # IP responds but is not in DB -> Add as conflict
                    try:
                        ip_service.assign_ip(
                            subnet_id=subnet.id,
                            address=ip_str,
                            status="conflict",
                            description="Discovered during automated ICMP sweep",
                        )
                        conflict_count += 1
                    except Exception as e:
                        logger.error(f"Failed to record conflict for {ip_str}: {e}")

        db.commit()
        logger.info(f"Sweep completed for {subnet.cidr}: {updated_count} IPs updated, {conflict_count} new conflicts found.")

    except Exception as e:
        logger.error(f"Sweep failed for subnet {subnet_id}: {e}")
    finally:
        db.close()
