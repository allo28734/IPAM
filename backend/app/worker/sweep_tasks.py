"""
Sweep background tasks — Worker logic.

This module contains the Celery task for performing ICMP ping sweeps.
Since Celery workers run in separate processes, each task must manage
its own database sessions using `SessionLocal()`.
"""

import logging
import asyncio
from datetime import datetime, timezone

from celery import shared_task
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.ip_address import IPAddress
from app.models.subnet import Subnet
from app.services.ip_address_service import IPAddressService
from app.utils.ip_utils import get_usable_host_range
from app.utils.ping_utils import ping_sweep

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def run_subnet_sweep(self, subnet_id: int):
    """
    Background Celery task to ping sweep a specific subnet.
    """
    db = SessionLocal()
    try:
        subnet = db.query(Subnet).filter(Subnet.id == subnet_id).first()
        if not subnet:
            logger.error(f"Sweep failed: Subnet {subnet_id} not found.")
            return {"error": "Subnet not found"}

        usable_ips = get_usable_host_range(subnet.cidr)
        if not usable_ips:
            return {"error": "No usable IPs in subnet"}

        # Sanity check limit (though API route should have enforced this)
        if len(usable_ips) > 2048:
            logger.warning(f"Subnet {subnet.cidr} exceeds 2048 IPs, capping sweep.")
            usable_ips = usable_ips[:2048]

        logger.info(f"Starting ICMP sweep of {len(usable_ips)} IPs in subnet {subnet.name} ({subnet.cidr})")
        
        # Celery tasks are synchronous by default. We run the async ping_sweep using asyncio.run
        results = asyncio.run(ping_sweep(usable_ips, max_concurrency=50))

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
        
        return {
            "subnet": subnet.cidr,
            "ips_swept": len(usable_ips),
            "updated_count": updated_count,
            "conflict_count": conflict_count
        }

    except Exception as e:
        logger.error(f"Sweep failed for subnet {subnet_id}: {e}")
        return {"error": str(e)}
    finally:
        db.close()
