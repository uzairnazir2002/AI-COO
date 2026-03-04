from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.services.report_service import ReportService


class _FakeS3:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[f"{Bucket}/{Key}"] = Body

    def generate_presigned_url(self, _, Params, ExpiresIn):
        return f"http://fake-minio/{Params['Bucket']}/{Params['Key']}?exp={ExpiresIn}"


class _FakeRepo:
    def __init__(self):
        self.db = object()
        self.saved = []

    async def list_reports(self, org_id):
        return self.saved

    async def get_by_week(self, org_id, week_start):
        return next((r for r in self.saved if r.org_id == org_id and r.week_start == week_start), None)

    async def save(self, report):
        report.id = uuid4()
        self.saved.append(report)
        return report


@pytest.mark.asyncio
async def test_report_generate_and_download_roundtrip(monkeypatch):
    fake_s3 = _FakeS3()
    repo = _FakeRepo()
    svc = ReportService(repo)

    monkeypatch.setattr("app.domain.services.report_service.s3_client", lambda: fake_s3)
    monkeypatch.setattr("app.domain.services.report_service.ensure_bucket", lambda client: None)

    class _Cfg:
        minio_bucket = "reports"

    monkeypatch.setattr("app.domain.services.report_service.get_settings", lambda: _Cfg())

    async def _ctx(*_args, **_kwargs):
        return {
            "summary": {
                "cash_balance": Decimal("1000.00"),
                "revenue_mtd": Decimal("400.00"),
                "expenses_mtd": Decimal("250.00"),
                "net_profit_mtd": Decimal("150.00"),
                "burn_rate_monthly": Decimal("50.00"),
                "alerts_count_open": 1,
            },
            "runway": {"monthly_burn": Decimal("50.00"), "runway_days": 600},
            "alerts": [SimpleNamespace(severity="HIGH", title="Expense spike")],
            "forecast": [
                SimpleNamespace(month=date(2026, 3, 1), revenue_pred=Decimal("420"), expense_pred=Decimal("260"))
            ],
            "ai_summary": SimpleNamespace(headline="Summary", highlights=["h1"], confidence="high"),
        }

    monkeypatch.setattr(svc, "_build_context", _ctx)

    org_id = uuid4()
    report = await svc.generate(org_id, date(2026, 3, 2), created_by=None)
    url = await svc.download_url(report)

    assert report.id is not None
    assert "fake-minio/reports/reports/" in url
    assert len(fake_s3.objects) == 1
    stored_pdf = next(iter(fake_s3.objects.values()))
    assert stored_pdf.startswith(b"%PDF")
