import logging

from celery import Celery
from celery.schedules import crontab

from app.config import settings

logger = logging.getLogger("app.celery")

celery_app = Celery(
    "stockflow",
    broker=settings.redis_url,
    include=["app.services.email_service", "app.services.scheduled_reports"],
)
celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "send-scheduled-stock-report": {
        "task": "app.services.scheduled_reports.send_scheduled_stock_report",
        "schedule": crontab(hour=6, minute=0),
    },
}


def enqueue(task, **kwargs) -> None:
    """Best-effort: a broker/connection failure enqueuing a job must not break the request that
    triggered it (mirrors email_service._send_best_effort's never-raises guarantee)."""
    try:
        task.delay(**kwargs)
    except Exception:
        logger.exception("Failed to enqueue task %s", getattr(task, "name", task))
