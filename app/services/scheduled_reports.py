from app.celery_app import celery_app
from app.crud import report as crud_report
from app.database import SessionLocal
from app.services import email_service


def _format_stock_valuation(report: dict) -> str:
    lines = [
        f"Total stock value: {report['total_value']}",
        f"Total stock quantity: {report['total_quantity']}",
        "",
        "By warehouse:",
    ]
    for row in report["by_warehouse"]:
        lines.append(f"  - {row['warehouse'].name}: {row['total_quantity']} units, value {row['total_value']}")
    lines.append("")
    lines.append("By category:")
    for row in report["by_category"]:
        lines.append(f"  - {row['category'].name}: {row['total_quantity']} units, value {row['total_value']}")
    return "\n".join(lines)


@celery_app.task(name="app.services.scheduled_reports.send_scheduled_stock_report")
def send_scheduled_stock_report() -> None:
    # Runs outside any FastAPI request (triggered by Celery beat), so there's no Depends(get_db)
    # to use - opens its own short-lived session, same pattern as
    # email_service._active_admin_emails.
    db = SessionLocal()
    try:
        report = crud_report.stock_valuation(db)
    finally:
        db.close()
    email_service.notify_stock_report(report_text=_format_stock_valuation(report))
