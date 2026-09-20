import logging
import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import Protocol

from app.celery_app import celery_app
from app.config import settings
from app.crud import user as crud_user
from app.database import SessionLocal
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
    # notifiers run as FastAPI BackgroundTasks, which execute after the request's own `db`
    # (app.database.get_db) has already been closed.
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
    _send_best_effort(
        subject=f"PO-{purchase_order_id} submitted",
        body=f"Purchase order PO-{purchase_order_id} to {supplier_name} has been submitted.",
    )


@celery_app.task(name="app.services.email_service.notify_purchase_order_received")
def notify_purchase_order_received(*, purchase_order_id: int, supplier_name: str) -> None:
    _send_best_effort(
        subject=f"PO-{purchase_order_id} received in full",
        body=f"Purchase order PO-{purchase_order_id} from {supplier_name} has been fully received.",
    )


@celery_app.task(name="app.services.email_service.notify_customer_order_shipped")
def notify_customer_order_shipped(*, customer_order_id: int, customer_name: str) -> None:
    _send_best_effort(
        subject=f"CO-{customer_order_id} fully shipped",
        body=f"Customer order CO-{customer_order_id} for {customer_name} has been fully shipped.",
    )


@celery_app.task(name="app.services.email_service.notify_low_stock")
def notify_low_stock(*, product_name: str, warehouse_name: str, quantity: int, threshold: int) -> None:
    _send_best_effort(
        subject=f"Low stock: {product_name} at {warehouse_name}",
        body=(
            f"{product_name} at {warehouse_name} has dropped to {quantity} units, "
            f"at or below the minimum threshold of {threshold}."
        ),
    )


def notify_stock_report(*, report_text: str) -> None:
    today = datetime.now(UTC).date()
    _send_best_effort(subject=f"Scheduled stock report - {today}", body=report_text)
