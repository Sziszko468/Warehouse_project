import logging

from celery import Celery
from celery.schedules import crontab
from kombu.exceptions import OperationalError

from app.config import settings

logger = logging.getLogger("app.celery")

# When the daily stock-report beat job fires.
STOCK_REPORT_SCHEDULE_HOUR_UTC = 6
STOCK_REPORT_SCHEDULE_MINUTE_UTC = 0

celery_app = Celery(
    "stockflow",
    broker=settings.redis_url,
    include=["app.services.email_service", "app.services.scheduled_reports"],
)
celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "send-scheduled-stock-report": {
        "task": "app.services.scheduled_reports.send_scheduled_stock_report",
        "schedule": crontab(hour=STOCK_REPORT_SCHEDULE_HOUR_UTC, minute=STOCK_REPORT_SCHEDULE_MINUTE_UTC),
    },
}


def enqueue(task, **kwargs) -> None:
    """Best-effort: a broker/connection failure enqueuing a job must not break the request that
    triggered it (mirrors email_service._send_best_effort's never-raises guarantee). Only swallows
    OperationalError (the broker is unreachable) - a bad call (wrong kwarg, missing argument) or a
    bug inside the task body (surfaced synchronously when Celery runs in eager mode, e.g. in tests)
    must still raise, or it would silently become a permanent no-op instead of failing loudly."""
    try:
        task.delay(**kwargs)
    except OperationalError:
        logger.exception("Failed to enqueue task %s: broker unreachable", getattr(task, "name", task))
