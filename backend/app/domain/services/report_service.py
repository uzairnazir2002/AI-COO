import io
from datetime import date, timedelta
from decimal import Decimal

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.core.config import get_settings
from app.domain.models.report import Report
from app.domain.repos.alerts_repo import AlertRepo
from app.domain.repos.analytics_repo import AnalyticsRepo
from app.domain.repos.forecast_repo import ForecastRepo
from app.domain.repos.report_repo import ReportRepo
from app.domain.services.ai_service import AIService
from app.domain.services.alerts_service import AlertsService
from app.domain.services.analytics_service import AnalyticsService
from app.domain.services.forecast_service import ForecastService
from app.infra.s3 import ensure_bucket, s3_client
from app.utils.idempotency import report_key


class ReportService:
    def __init__(self, repo: ReportRepo):
        self.repo = repo

    async def list_reports(self, org_id):
        return await self.repo.list_reports(org_id)

    async def generate(self, org_id, week_start: date, created_by=None):
        existing = await self.repo.get_by_week(org_id, week_start)
        if existing:
            return existing
        week_end = week_start + timedelta(days=6)
        context = await self._build_context(org_id, week_start, week_end)
        file_key = report_key(str(org_id), week_start)
        content = self._build_pdf(org_id, week_start, week_end, context)
        s3 = s3_client()
        ensure_bucket(s3)
        bucket = get_settings().minio_bucket
        s3.put_object(Bucket=bucket, Key=file_key, Body=content, ContentType="application/pdf")
        report = Report(org_id=org_id, week_start=week_start, week_end=week_end, file_key=file_key, created_by=created_by)
        return await self.repo.save(report)

    async def download_url(self, report: Report):
        s3 = s3_client()
        bucket = get_settings().minio_bucket
        return s3.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": report.file_key}, ExpiresIn=3600
        )

    async def _build_context(self, org_id, week_start: date, week_end: date) -> dict:
        db = self.repo.db
        analytics = AnalyticsService(AnalyticsRepo(db))
        summary = await analytics.summary(org_id, week_start, week_end)
        runway = await analytics.runway(org_id, 6, conservative=False)

        alerts_service = AlertsService(db, AlertRepo(db))
        await alerts_service.detect_and_create(org_id)
        alerts = await alerts_service.list_alerts(org_id, "OPEN")

        forecast_rows = await ForecastService(ForecastRepo(db), AnalyticsRepo(db)).ensure_forecasts(org_id, 3)
        base_forecast = [f for f in forecast_rows if str(f.scenario).upper() == "BASE"][:3]

        ai_payload = {
            "kpis": summary,
            "alerts": [{"title": a.title, "severity": a.severity} for a in alerts[:5]],
        }
        ai_summary = await AIService().summary(ai_payload)
        return {
            "summary": summary,
            "runway": runway,
            "alerts": alerts,
            "forecast": base_forecast,
            "ai_summary": ai_summary.summary_json,
        }

    @staticmethod
    def _fmt_money(value: Decimal | int | float) -> str:
        return f"${Decimal(value):,.2f}"

    def _build_pdf(self, org_id, week_start, week_end, context: dict) -> bytes:
        buf = io.BytesIO()
        pdf = canvas.Canvas(buf, pagesize=letter)
        y = 760
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(72, y, "AI COO Weekly Report")
        y -= 24

        pdf.setFont("Helvetica", 10)
        pdf.drawString(72, y, f"Organization: {org_id}")
        y -= 14
        pdf.drawString(72, y, f"Week: {week_start} to {week_end}")
        y -= 24

        summary = context["summary"]
        runway = context["runway"]
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(72, y, "KPI Summary")
        y -= 16
        pdf.setFont("Helvetica", 10)
        pdf.drawString(72, y, f"Cash balance: {self._fmt_money(summary['cash_balance'])}")
        y -= 14
        pdf.drawString(72, y, f"Revenue MTD: {self._fmt_money(summary['revenue_mtd'])}")
        y -= 14
        pdf.drawString(72, y, f"Expenses MTD: {self._fmt_money(summary['expenses_mtd'])}")
        y -= 14
        pdf.drawString(72, y, f"Net profit MTD: {self._fmt_money(summary['net_profit_mtd'])}")
        y -= 14
        pdf.drawString(72, y, f"Monthly burn: {self._fmt_money(runway['monthly_burn'])}")
        y -= 14
        pdf.drawString(72, y, f"Runway days: {runway['runway_days']}")
        y -= 22

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(72, y, "Base Forecast (3 Months)")
        y -= 16
        pdf.setFont("Helvetica", 10)
        for point in context["forecast"]:
            pdf.drawString(
                72,
                y,
                f"{point.month}: rev {self._fmt_money(point.revenue_pred)}, exp {self._fmt_money(point.expense_pred)}",
            )
            y -= 14

        y -= 8
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(72, y, "Open Alerts")
        y -= 16
        pdf.setFont("Helvetica", 10)
        alerts = context["alerts"][:5]
        if not alerts:
            pdf.drawString(72, y, "No open alerts.")
            y -= 14
        else:
            for alert in alerts:
                pdf.drawString(72, y, f"[{alert.severity}] {alert.title}")
                y -= 14

        y -= 8
        ai = context["ai_summary"]
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(72, y, "Executive Summary")
        y -= 16
        pdf.setFont("Helvetica", 10)
        pdf.drawString(72, y, ai.headline)
        y -= 14
        for line in ai.highlights[:3]:
            pdf.drawString(72, y, f"- {line[:95]}")
            y -= 14
        pdf.drawString(72, y, f"Confidence: {ai.confidence}")

        pdf.showPage()
        pdf.save()
        buf.seek(0)
        return buf.read()
