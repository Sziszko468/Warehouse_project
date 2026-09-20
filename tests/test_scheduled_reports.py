import pytest

from app.services import email_service, scheduled_reports


class RecordingEmailSender:
    def __init__(self):
        self.sent = []

    def send(self, *, to, subject, body):
        self.sent.append({"to": to, "subject": subject, "body": body})


@pytest.fixture
def recorder(monkeypatch, scheduled_reports_session):
    rec = RecordingEmailSender()
    monkeypatch.setattr(email_service, "get_email_sender", lambda: rec)
    monkeypatch.setattr(email_service, "_active_admin_emails", lambda: ["admin@stockflow.com"])
    return rec


def test_scheduled_stock_report_sends_email_with_totals(
    client, admin_headers, db_session, recorder, category_id, warehouse_a_id, product_id
):
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 10},
        headers=admin_headers,
    )
    # send_scheduled_stock_report reads through a different Session than db_session - commit so
    # it's visible there.
    db_session.commit()

    scheduled_reports.send_scheduled_stock_report()

    assert len(recorder.sent) == 1
    email = recorder.sent[0]
    assert email["to"] == ["admin@stockflow.com"]
    assert "Scheduled stock report" in email["subject"]
    assert "Total stock value: 99.90" in email["body"]
    assert "Total stock quantity: 10" in email["body"]
    assert "Warehouse A: 10 units, value 99.90" in email["body"]
    assert "Cables: 10 units, value 99.90" in email["body"]


def test_scheduled_stock_report_with_no_stock_sends_zero_totals(client, admin_headers, recorder):
    scheduled_reports.send_scheduled_stock_report()

    assert len(recorder.sent) == 1
    body = recorder.sent[0]["body"]
    assert "Total stock value: 0" in body
    assert "Total stock quantity: 0" in body


def test_beat_schedule_includes_scheduled_stock_report():
    from app.celery_app import celery_app

    entry = celery_app.conf.beat_schedule["send-scheduled-stock-report"]
    assert entry["task"] == "app.services.scheduled_reports.send_scheduled_stock_report"
