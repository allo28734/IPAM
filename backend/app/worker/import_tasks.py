"""
Bulk import background tasks — Worker logic.

This module contains the Celery task for processing CSV subnet
imports in the background to prevent blocking the API event loop.
"""

import csv
import io
import logging

from celery import shared_task
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.subnet_service import SubnetService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def run_bulk_subnet_import(self, csv_text: str):
    """
    Background Celery task to import subnets from CSV text.

    Receives the CSV content as a string (already read from the
    uploaded file by the API route) and delegates to SubnetService.
    """
    db = SessionLocal()
    try:
        csv_file_obj = io.StringIO(csv_text)
        service = SubnetService(db)
        result = service.bulk_import(csv_file_obj)

        logger.info(
            "Bulk import completed: %d imported, %d errors",
            result["imported"],
            len(result["errors"]),
        )
        return result

    except Exception as e:
        logger.error("Bulk import failed: %s", e)
        return {"imported": 0, "errors": [str(e)]}
    finally:
        db.close()
