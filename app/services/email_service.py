import logging
import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import Protocol

from app.celery_app import celery_app
from app.config import settings
from app.crud import user as crud_user
from app.database import SessionLocal
from app.messages import NotificationMessages
from app.models.user import UserRole

logger = logging.getLogger("app.email")


class EmailSender(Protocol):
    def send(self, *, to: list[str], subject: str, body: str) -> None: ...


class LogEmailSender:
    """Default sender - never touches a real mail server. Safe for local dev and tests."""

    def send(self, *, to: list[str], subject: str, body: str) -> None:
        logger.info("Email (not sent, email_backend=log) to=%s subject=%r\n%s", to, subject, body)


class SmtpEmailSender:
    def send(self, *, to: list[str], subject: str, body: str) -> None:
        if not to:
            return
        message = EmailMessage()
        message["From"] = settings.smtp_from_email
        message["To"] = ", ".join(to)
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)


def get_email_sender() -> EmailSender:
    if settings.email_backend == "smtp":
        return SmtpEmailSender()
    return LogEmailSender()


def _active_admin_emails() -> list[str]:
    # Opens its own short-lived session rather than reusing the triggering request's - these
    # notifiers run as Celery tasks, in a separate worker process where the request's own `db`
    # (app.database.get_db) was never available in the first place.
    db = SessionLocal()
    try:
        admins, _ = crud_user.list_users(db, role=UserRole.ADMIN, is_active=True, limit=1000)
        return [admin.email for admin in admins]
    finally:
        db.close()


def _send_best_effort(*, subject: str, body: str) -> None:
    """Never raises - a notification failure must not affect the request that triggered it."""
    try:
        to = _active_admin_emails()
        get_email_sender().send(to=to, subject=subject, body=body)
    except Exception:
        logger.exception("Failed to send email: subject=%r", subject)


@celery_app.task(name="app.services.email_service.notify_purchase_order_submitted")
def notify_purchase_order_submitted(*, purchase_order_id: int, supplier_name: str) -> None:
    subject, body = NotificationMessages.purchase_order_submitted(
        purchase_order_id=purchase_order_id, supplier_name=supplier_name
    )
    _send_best_effort(subject=subject, body=body)


@celery_app.task(name="app.services.email_service.notify_purchase_order_received")
def notify_purchase_order_received(*, purchase_order_id: int, supplier_name: str) -> None:
    subject, body = NotificationMessages.purchase_order_received(
        purchase_order_id=purchase_order_id, supplier_name=supplier_name
    )
    _send_best_effort(subject=subject, body=body)


@celery_app.task(name="app.services.email_service.notify_customer_order_shipped")
def notify_customer_order_shipped(*, customer_order_id: int, customer_name: str) -> None:
    subject, body = NotificationMessages.customer_order_shipped(
        customer_order_id=customer_order_id, customer_name=customer_name
    )
    _send_best_effort(subject=subject, body=body)


@celery_app.task(name="app.services.email_service.notify_low_stock")
def notify_low_stock(*, product_name: str, warehouse_name: str, quantity: int, threshold: int) -> None:
    subject, body = NotificationMessages.low_stock(
        product_name=product_name, warehouse_name=warehouse_name, quantity=quantity, threshold=threshold
    )
    _send_best_effort(subject=subject, body=body)


def notify_stock_report(*, report_text: str) -> None:
    # Not a @celery_app.task itself, unlike the notify_* functions above - it's only ever called
    # in-process from inside app.services.scheduled_reports.send_scheduled_stock_report, which is
    # already the task doing the async dispatch. Wrapping it as a task too would double-enqueue.
    today = datetime.now(UTC).date()
    subject = NotificationMessages.stock_report(report_date=str(today))
    _send_best_effort(subject=subject, body=report_text)
