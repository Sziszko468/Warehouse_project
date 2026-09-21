from app.messages import Messages, NotificationMessages


def _string_constants(cls) -> list[str]:
    attrs = (getattr(cls, name) for name in dir(cls) if not name.startswith("_"))
    return [attr for attr in attrs if isinstance(attr, str)]


def test_messages_are_ascii_only():
    # Guards against hardcoded Hungarian (or any other non-ASCII) text creeping into API error
    # details or notification text - these live in one place specifically so they stay
    # translatable, in English, rather than scattered literals in a mixed language.
    for value in _string_constants(Messages):
        assert value.isascii(), f"Non-ASCII text in Messages: {value!r}"


def test_notification_messages_are_ascii_only():
    subject, body = NotificationMessages.purchase_order_submitted(purchase_order_id=1, supplier_name="Acme")
    assert subject.isascii()
    assert body.isascii()


def test_notification_messages_purchase_order_submitted():
    subject, body = NotificationMessages.purchase_order_submitted(purchase_order_id=7, supplier_name="Acme Corp")
    assert subject == "PO-7 submitted"
    assert "PO-7" in body
    assert "Acme Corp" in body


def test_notification_messages_purchase_order_received():
    subject, body = NotificationMessages.purchase_order_received(purchase_order_id=7, supplier_name="Acme Corp")
    assert subject == "PO-7 received in full"
    assert "Acme Corp" in body


def test_notification_messages_customer_order_shipped():
    subject, body = NotificationMessages.customer_order_shipped(customer_order_id=3, customer_name="Contoso")
    assert subject == "CO-3 fully shipped"
    assert "Contoso" in body


def test_notification_messages_low_stock():
    subject, body = NotificationMessages.low_stock(
        product_name="USB Cable", warehouse_name="Warehouse A", quantity=2, threshold=5
    )
    assert subject == "Low stock: USB Cable at Warehouse A"
    assert "2 units" in body
    assert "5" in body


def test_notification_messages_stock_report():
    assert NotificationMessages.stock_report(report_date="2026-09-21") == "Scheduled stock report - 2026-09-21"
