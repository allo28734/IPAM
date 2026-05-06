"""
Sweep background tasks — Worker logic.

This module contains the Celery task for performing ICMP ping sweeps.
Since Celery workers run in separate processes, each task must manage
its own database sessions.

CRITICAL: AsyncSession instances are bound to the event loop that
created them. All async DB logic runs inside an `async def` wrapper
invoked via `asyncio.run()`, and the session is created INSIDE that
wrapper — never in the synchronous Celery task scope.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update

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


async def _async_run_sweep(subnet_id: int) -> dict:
    """
    Async implementation of the subnet sweep.

    The AsyncSession is created here, inside the async function,
    so it is bound to the event loop started by asyncio.run().
    """
    async with SessionLocal() as db:
        # Fetch the subnet
        subnet = await db.get(Subnet, subnet_id)
        if not subnet:
            logger.error(f"Sweep failed: Subnet {subnet_id} not found.")
            return {"error": "Subnet not found"}

        import ipaddress
        network = ipaddress.ip_network(subnet.cidr, strict=False)
        if network.version == 4 and network.prefixlen >= 31:
            usable_ips = [str(ip) for ip in network]
        elif network.version == 6 and network.prefixlen == 128:
            usable_ips = [str(ip) for ip in network]
        else:
            usable_ips = [str(ip) for ip in network.hosts()]

        if not usable_ips:
            return {"error": "No usable IPs in subnet"}

        # Sanity check limit (though API route should have enforced this)
        if len(usable_ips) > 2048:
            logger.warning(f"Subnet {subnet.cidr} exceeds 2048 IPs, capping sweep.")
            usable_ips = usable_ips[:2048]

        logger.info(
            f"Starting ICMP sweep of {len(usable_ips)} IPs in subnet "
            f"{subnet.name} ({subnet.cidr})"
        )

        # ping_sweep is already async
        results = await ping_sweep(usable_ips, max_concurrency=50)

        # Build service for auditing and creating IPs
        ip_service = IPAddressService(db)

        snmp_credentials = None
        if subnet.discovery_profile_id:
            try:
                profile_service = DiscoveryProfileService(db)
                snmp_credentials = await profile_service.get_decrypted_credentials(
                    subnet.discovery_profile_id
                )
            except Exception as e:
                logger.error(
                    f"Failed to load SNMP credentials for subnet {subnet_id}: {e}"
                )

        # Fetch existing IPs from the DB using lightweight column selection
        existing_stmt = (
            select(IPAddress.address, IPAddress.id, IPAddress.status)
            .where(IPAddress.subnet_id == subnet.id)
        )
        existing_result = await db.execute(existing_stmt)
        existing_ips_map = {row.address: row for row in existing_result.all()}

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
                    await db.execute(
                        update(IPAddress)
                        .where(IPAddress.id == existing_ip.id)
                        .values(last_seen=datetime.now(timezone.utc))
                    )

                    updated_count += 1

                    status_update = None
                    if existing_ip.status == "available":
                        status_update = "conflict"
                        conflict_count += 1

                    await ip_service.update_ip(
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
                        new_ip = await ip_service.assign_ip(
                            subnet_id=subnet.id,
                            address=ip_str,
                            status="conflict",
                            description="Discovered during automated ICMP sweep",
                        )
                        # Now update it with discovery data
                        await ip_service.update_ip(
                            new_ip.id,
                            mac_address=discovery_data.get("mac_address"),
                            vendor=discovery_data.get("vendor"),
                            os_guess=discovery_data.get("os_guess"),
                            device_type=discovery_data.get("device_type"),
                        )
                        conflict_count += 1
                    except Exception as e:
                        logger.error(f"Failed to record conflict for {ip_str}: {e}")

        await db.commit()
        logger.info(
            f"Sweep completed for {subnet.cidr}: {updated_count} IPs updated, "
            f"{conflict_count} new conflicts found."
        )

        return {
            "subnet": subnet.cidr,
            "ips_swept": len(usable_ips),
            "updated_count": updated_count,
            "conflict_count": conflict_count,
        }


@celery_app.task(bind=True)
def run_subnet_sweep(self, subnet_id: int):
    """
    Synchronous Celery task entry point.

    Delegates to the async implementation via asyncio.run().
    """
    try:
        return asyncio.run(_async_run_sweep(subnet_id))
    except Exception as e:
        logger.error(f"Sweep failed for subnet {subnet_id}: {e}")
        return {"error": str(e)}


async def _async_sweep_all() -> dict:
    """Async helper: query all subnet IDs and dispatch individual sweeps."""
    async with SessionLocal() as db:
        result = await db.scalars(select(Subnet.id))
        subnet_ids = list(result.all())

    logger.info("Beat: dispatching sweeps for %d subnets", len(subnet_ids))
    for sid in subnet_ids:
        run_subnet_sweep.delay(sid)
    return {"dispatched": len(subnet_ids)}


@celery_app.task
def sweep_all_subnets():
    """
    Periodic task (called by Celery Beat).

    Queries every subnet in the database and fans out individual
    run_subnet_sweep tasks so they execute concurrently across
    available workers.
    """
    try:
        return asyncio.run(_async_sweep_all())
    except Exception as e:
        logger.error("sweep_all_subnets failed: %s", e)
        return {"error": str(e)}
