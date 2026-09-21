import pytest
from kombu.exceptions import OperationalError

from app.celery_app import enqueue


class _FakeTask:
    name = "fake.task"

    def __init__(self, delay_side_effect=None):
        self.delay_side_effect = delay_side_effect
        self.calls: list[dict] = []

    def delay(self, **kwargs):
        self.calls.append(kwargs)
        if self.delay_side_effect is not None:
            raise self.delay_side_effect


def test_enqueue_delivers_kwargs_to_the_task():
    task = _FakeTask()

    enqueue(task, purchase_order_id=1, supplier_name="Acme")

    assert task.calls == [{"purchase_order_id": 1, "supplier_name": "Acme"}]


def test_enqueue_swallows_broker_connection_failure():
    # A dead/unreachable Redis broker must not break the request that triggered the enqueue -
    # this is the whole point of enqueue() existing rather than calling task.delay() directly.
    task = _FakeTask(delay_side_effect=OperationalError("broker unreachable"))

    enqueue(task, foo="bar")  # must not raise


def test_enqueue_does_not_swallow_a_programmer_error():
    # A bug in the call site (wrong/missing kwarg) or in the task body itself (surfaced
    # synchronously here since tests run Celery in eager mode) must fail loudly rather than
    # silently becoming a permanent no-op - only broker connectivity failures are best-effort.
    task = _FakeTask(delay_side_effect=TypeError("unexpected keyword argument"))

    with pytest.raises(TypeError):
        enqueue(task, foo="bar")


def test_send_scheduled_stock_report_has_a_retry_policy():
    from app.services import scheduled_reports

    task = scheduled_reports.send_scheduled_stock_report
    assert task.max_retries == scheduled_reports.REPORT_TASK_MAX_RETRIES
    assert Exception in task.autoretry_for
