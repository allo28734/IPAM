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
from app.utils.discovery_utils import fingerprint_ip
from app.utils.snmp_utils import poll_snmpv3
from app.services.discovery_profile_service import DiscoveryProfileService

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

        snmp_credentials = None
        if subnet.discovery_profile_id:
            try:
                profile_service = DiscoveryProfileService(db)
                snmp_credentials = profile_service.get_decrypted_credentials(subnet.discovery_profile_id)
            except Exception as e:
                logger.error(f"Failed to load SNMP credentials for subnet {subnet_id}: {e}")

        # Fetch existing IPs from the DB using with_entities to avoid massive ORM bloat
        existing_ips_query = db.query(IPAddress).with_entities(IPAddress.address, IPAddress.id, IPAddress.status).filter(IPAddress.subnet_id == subnet.id).all()
        existing_ips_map = {row.address: row for row in existing_ips_query}

        conflict_count = 0
        updated_count = 0

        for ip_str, is_alive in results.items():
            if is_alive:
                discovery_data = {}
                if snmp_credentials:
                    snmp_data = poll_snmpv3(ip_str, snmp_credentials)
                    if any(v for v in snmp_data.values()):
                        discovery_data = snmp_data
                
                # Fallback to Nmap fingerprinting if SNMP fails or isn't configured
                if not discovery_data:
                    discovery_data = fingerprint_ip(ip_str)

                if ip_str in existing_ips_map:
                    existing_ip = existing_ips_map[ip_str]
                    
                    # Update last seen directly using an update statement
                    db.query(IPAddress).filter(IPAddress.id == existing_ip.id).update({"last_seen": datetime.now(timezone.utc)})
                    
                    updated_count += 1
                    
                    status_update = None
                    if existing_ip.status == "available":
                        status_update = "conflict"
                        conflict_count += 1
                        
                    ip_service.update_ip(
                        existing_ip.id,
                        status=status_update,
                        mac_address=discovery_data.get("mac_address"),
                        vendor=discovery_data.get("vendor"),
                        os_guess=discovery_data.get("os_guess"),
                        device_type=discovery_data.get("device_type"),
                    )
                else:
                    # IP responds but is not in DB -> Add as conflict
                    try:
                        new_ip = ip_service.assign_ip(
                            subnet_id=subnet.id,
                            address=ip_str,
                            status="conflict",
                            description="Discovered during automated ICMP sweep",
                        )
                        # Now update it with discovery data
                        ip_service.update_ip(
                            new_ip.id,
                            mac_address=discovery_data.get("mac_address"),
                            vendor=discovery_data.get("vendor"),
                            os_guess=discovery_data.get("os_guess"),
                            device_type=discovery_data.get("device_type"),
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
