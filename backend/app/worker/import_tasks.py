"""
Bulk import background tasks — Worker logic.

This module contains the Celery task for processing CSV subnet
imports in the background to prevent blocking the API event loop.

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

logger = logging.getLogger(__name__)


async def _async_run_bulk_import(csv_text: str) -> dict:
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
            "Bulk import completed: %d imported, %d errors",
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
        return asyncio.run(_async_run_bulk_import(csv_text))
    except Exception as e:
        logger.error("Bulk import failed: %s", e)
        return {"imported": 0, "errors": [str(e)]}
