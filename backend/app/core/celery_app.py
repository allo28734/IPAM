"""
Celery Application Configuration.

Configures the Celery instance used for background tasks (e.g., ICMP sweeps)
using Redis as both the message broker and the result backend.
"""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "ipam_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # In a real production environment, you might want task routing, rate limits, etc.
)

# Auto-discover tasks in the app.worker package
celery_app.autodiscover_tasks(["app.worker"])
