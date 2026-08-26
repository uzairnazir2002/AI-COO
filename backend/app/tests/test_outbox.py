import uuid
from datetime import date

import pytest

from app.domain.models.report import Report
from app.domain.services.report_service import ReportService
from app.infra.email import SendEmailResult


class _ScalarRows:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _Rows:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return _ScalarRows(self._values)


class _FakeDB:
    def __init__(self, recipients):
        self.recipients = recipients

    async def execute(self, _stmt):
        return _Rows(self.recipients)


class _FakeReportRepo:
    def __init__(self, report: Report, recipients: list[str]):
        self._report = report
        self.db = _FakeDB(recipients)

    async def get_by_week(self, _org_id, _week_start, *, location_id=None):
        return self._report

    async def save(self, report):
        return report


@pytest.mark.asyncio
async def test_report_generation_enqueues_outbox_event(monkeypatch):
    report = Report(
        org_id=uuid.uuid4(),
        week_start=date(2026, 3, 2),
        week_end=date(2026, 3, 8),
        file_key="reports/test.pdf",
        created_by=None,
    )
    report.id = uuid.uuid4()
    repo = _FakeReportRepo(report, ["owner@example.com", "editor@example.com"])
    svc = ReportService(repo)  # type: ignore[arg-type]

    created: list[dict] = []

    class _FakeOutboxRepo:
        def __init__(self, _db):
            pass

        async def create_event(self, **kwargs):
            created.append(kwargs)
            return None

    async def _download_url(_self, _report):
        return "http://example.com/report.pdf"

    monkeypatch.setattr("app.domain.services.report_service.OutboxRepo", _FakeOutboxRepo)
    monkeypatch.setattr(ReportService, "download_url", _download_url)

    out = await svc.generate(report.org_id, report.week_start, report.created_by)
    assert out.id == report.id
    assert len(created) == 2
    assert created[0]["event_type"] == "email.send"
    assert "weekly report" in created[0]["payload"]["subject"].lower()


class _FakeAsyncSession:
    def __init__(self):
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def commit(self):
        self.commits += 1


class _FakeEvent:
    def __init__(self, *, event_type: str, payload: dict, attempts: int = 0, max_attempts: int = 5):
        self.event_type = event_type
        self.payload = payload
        self.attempts = attempts
        self.max_attempts = max_attempts
        self.status = "PROCESSING"
        self.last_error: str | None = None


class _FakeDeliveryRepo:
    def __init__(self, _db):
        pass

    async def mark_sent(self, **_kwargs):
        return None

    async def mark_failed(self, **_kwargs):
        return None

    async def mark_retrying(self, **_kwargs):
        return None


@pytest.mark.asyncio
async def test_outbox_consumer_sends_and_marks_delivered(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from importlib import reload
    import app.jobs.tasks.outbox as outbox_tasks

    outbox_tasks = reload(outbox_tasks)
    fake_session = _FakeAsyncSession()
    sent: list[tuple[str, str]] = []

    event = _FakeEvent(
        event_type="email.send",
        payload={"to": "owner@example.com", "subject": "s", "body": "b"},
    )

    class _FakeOutboxRepo:
        def __init__(self, _db):
            pass

        async def claim_pending(self, limit: int):
            assert limit == 100
            return [event]

        async def mark_sent(self, ev):
            ev.status = "SENT"

        async def mark_sent_dry_run(self, ev):
            ev.status = "SENT_DRY_RUN"

        async def mark_retry_or_failed(self, ev, _error: str):
            ev.status = "FAILED"
            ev.last_error = _error

    def _send_email(to: str, subject: str, _body: str, html_body: str | None = None):
        assert html_body is None
        sent.append((to, subject))
        return SendEmailResult(status="sent", provider="smtp")

    monkeypatch.setattr(outbox_tasks, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(outbox_tasks, "OutboxRepo", _FakeOutboxRepo)
    monkeypatch.setattr(outbox_tasks, "WorkforceAnnouncementDeliveryRepo", _FakeDeliveryRepo)
    monkeypatch.setattr(outbox_tasks, "send_email", _send_email)

    processed = await outbox_tasks._process(100)
    assert processed == 1
    assert event.status == "SENT"
    assert sent == [("owner@example.com", "s")]


@pytest.mark.asyncio
async def test_outbox_consumer_retries_then_fails(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from importlib import reload
    import app.jobs.tasks.outbox as outbox_tasks

    outbox_tasks = reload(outbox_tasks)
    fake_session = _FakeAsyncSession()
    retry_event = _FakeEvent(
        event_type="email.send",
        payload={"to": "r@example.com", "subject": "s", "body": "b"},
        attempts=0,
        max_attempts=2,
    )
    fail_event = _FakeEvent(
        event_type="email.send",
        payload={"to": "f@example.com", "subject": "s", "body": "b"},
        attempts=1,
        max_attempts=2,
    )

    class _FakeOutboxRepo:
        def __init__(self, _db):
            pass

        async def claim_pending(self, limit: int):
            assert limit == 50
            return [retry_event, fail_event]

        async def mark_sent(self, ev):
            ev.status = "SENT"

        async def mark_sent_dry_run(self, ev):
            ev.status = "SENT_DRY_RUN"

        async def mark_retry_or_failed(self, ev, _error: str):
            ev.attempts += 1
            ev.last_error = _error
            if ev.attempts >= ev.max_attempts:
                ev.status = "FAILED"
            else:
                ev.status = "RETRYING"

    def _send_email(_to: str, _subject: str, _body: str, html_body: str | None = None):
        assert html_body is None
        return SendEmailResult(status="failed", provider="smtp", error_message="smtp down")

    monkeypatch.setattr(outbox_tasks, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(outbox_tasks, "OutboxRepo", _FakeOutboxRepo)
    monkeypatch.setattr(outbox_tasks, "WorkforceAnnouncementDeliveryRepo", _FakeDeliveryRepo)
    monkeypatch.setattr(outbox_tasks, "send_email", _send_email)

    processed = await outbox_tasks._process(50)
    assert processed == 2
    assert retry_event.status == "RETRYING"
    assert fail_event.status == "FAILED"


@pytest.mark.asyncio
async def test_outbox_consumer_marks_dry_run_email(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from importlib import reload
    import app.jobs.tasks.outbox as outbox_tasks

    outbox_tasks = reload(outbox_tasks)
    fake_session = _FakeAsyncSession()

    event = _FakeEvent(
        event_type="email.send",
        payload={"to": "owner@example.com", "subject": "s", "body": "b"},
    )

    class _FakeOutboxRepo:
        def __init__(self, _db):
            pass

        async def claim_pending(self, limit: int):
            assert limit == 25
            return [event]

        async def mark_sent(self, ev):
            ev.status = "SENT"

        async def mark_sent_dry_run(self, ev):
            ev.status = "SENT_DRY_RUN"

        async def mark_retry_or_failed(self, ev, _error: str):
            ev.status = "FAILED"
            ev.last_error = _error

    def _send_email(_to: str, _subject: str, _body: str, html_body: str | None = None):
        assert html_body is None
        return SendEmailResult(status="sent_dry_run", provider="dry_run")

    monkeypatch.setattr(outbox_tasks, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(outbox_tasks, "OutboxRepo", _FakeOutboxRepo)
    monkeypatch.setattr(outbox_tasks, "WorkforceAnnouncementDeliveryRepo", _FakeDeliveryRepo)
    monkeypatch.setattr(outbox_tasks, "send_email", _send_email)

    processed = await outbox_tasks._process(25)
    assert processed == 1
    assert event.status == "SENT_DRY_RUN"
