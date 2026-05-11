"""
Bulk import background tasks — Worker logic.

This module contains Celery tasks for processing CSV imports
(subnets and IP addresses) in the background to prevent blocking
the API event loop.

CRITICAL: AsyncSession instances are bound to the event loop that
created them. All async DB logic runs inside an `async def` wrapper
invoked via `asyncio.run()`, and the session is created INSIDE that
wrapper — never in the synchronous Celery task scope.
"""

import asyncio
import io
import logging

from celery import shared_task
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.subnet_service import SubnetService
from app.services.ip_address_service import IPAddressService

logger = logging.getLogger(__name__)


# ── Subnet Bulk Import ─────────────────────────────────────────


async def _async_run_bulk_subnet_import(csv_text: str) -> dict:
    """
    Async implementation of the bulk subnet import.

    The AsyncSession is created here, inside the async function,
    so it is bound to the event loop started by asyncio.run().
    """
    async with SessionLocal() as db:
        csv_file_obj = io.StringIO(csv_text)
        service = SubnetService(db)
        result = await service.bulk_import(csv_file_obj)

        logger.info(
            "Bulk subnet import completed: %d imported, %d errors",
            result["imported"],
            len(result["errors"]),
        )
        return result


@celery_app.task(bind=True)
def run_bulk_subnet_import(self, csv_text: str):
    """
    Background Celery task to import subnets from CSV text.

    Receives the CSV content as a string (already read from the
    uploaded file by the API route) and delegates to SubnetService
    via an async wrapper.
    """
    try:
        return asyncio.run(_async_run_bulk_subnet_import(csv_text))
    except Exception as e:
        logger.error("Bulk subnet import failed: %s", e)
        return {"imported": 0, "errors": [str(e)]}


# ── IP Address Bulk Import ─────────────────────────────────────


async def _async_run_bulk_ip_import(subnet_id: int, csv_text: str) -> dict:
    """
    Async implementation of the bulk IP address import.

    The AsyncSession is created here, inside the async function,
    so it is bound to the event loop started by asyncio.run().
    """
    async with SessionLocal() as db:
        csv_file_obj = io.StringIO(csv_text)
        service = IPAddressService(db)
        result = await service.bulk_import(subnet_id, csv_file_obj)

        logger.info(
            "Bulk IP import completed for subnet %d: %d imported, %d errors",
            subnet_id,
            result["imported"],
            len(result["errors"]),
        )
        return result


@celery_app.task(bind=True)
def run_bulk_ip_import(self, subnet_id: int, csv_text: str):
    """
    Background Celery task to import IP addresses from CSV text.

    Receives the subnet ID and CSV content as a string (already
    read from the uploaded file by the API route) and delegates
    to IPAddressService via an async wrapper.
    """
    try:
        return asyncio.run(_async_run_bulk_ip_import(subnet_id, csv_text))
    except Exception as e:
        logger.error("Bulk IP import failed for subnet %d: %s", subnet_id, e)
        return {"imported": 0, "errors": [str(e)]}
