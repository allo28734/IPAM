"""
Integration sync background tasks — Worker logic.

Celery tasks for syncing vendor integration providers.
Follows the same asyncio.run() wrapper pattern used by sweep_tasks.py.

CRITICAL: AsyncSession instances are bound to the event loop that
created them. All async DB logic runs inside an `async def` wrapper
invoked via `asyncio.run()`, and the session is created INSIDE that
wrapper — never in the synchronous Celery task scope.
"""

import asyncio
import logging

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.integration_provider import IntegrationProvider
from app.services.integration_service import IntegrationService

logger = logging.getLogger(__name__)


async def _async_sync_integration(provider_id: int) -> dict:
    """
    Async implementation of a single integration sync.

    The AsyncSession is created here, inside the async function,
    so it is bound to the event loop started by asyncio.run().
    """
    async with SessionLocal() as db:
        service = IntegrationService(db)
        return await service.run_sync(provider_id)


@celery_app.task(bind=True)
def sync_integration(self, provider_id: int):
    """
    Synchronous Celery task entry point for a single provider sync.

    Delegates to the async implementation via asyncio.run().
    """
    try:
        result = asyncio.run(_async_sync_integration(provider_id))
        logger.info(
            f"Integration sync completed for provider {provider_id}: "
            f"{result.get('clients_enriched', 0)} clients enriched, "
            f"{result.get('networks_found', 0)} networks found"
        )
        return result
    except Exception as e:
        logger.error(f"Integration sync failed for provider {provider_id}: {e}")
        return {"error": str(e), "provider_id": provider_id}


async def _async_sync_all() -> dict:
    """Async helper: query all enabled provider IDs and dispatch individual syncs."""
    async with SessionLocal() as db:
        stmt = (
            select(IntegrationProvider.id)
            .where(IntegrationProvider.is_enabled == True)
        )
        result = await db.scalars(stmt)
        provider_ids = list(result.all())

    logger.info("Beat: dispatching integration syncs for %d providers", len(provider_ids))
    for pid in provider_ids:
        sync_integration.delay(pid)
    return {"dispatched": len(provider_ids)}


@celery_app.task
def sync_all_integrations():
    """
    Periodic task (called by Celery Beat).

    Queries every enabled integration provider and fans out individual
    sync_integration tasks so they execute concurrently across
    available workers.
    """
    try:
        return asyncio.run(_async_sync_all())
    except Exception as e:
        logger.error("sync_all_integrations failed: %s", e)
        return {"error": str(e)}
