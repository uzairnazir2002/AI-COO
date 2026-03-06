import uuid

import structlog
from celery import shared_task

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.domain.repos.alerts_repo import AlertRepo
from app.domain.repos.analytics_repo import AnalyticsRepo
from app.domain.repos.forecast_repo import ForecastRepo
from app.domain.repos.report_repo import ReportRepo
from app.domain.services.alerts_service import AlertsService
from app.domain.services.analytics_service import AnalyticsService
from app.domain.services.forecast_service import ForecastService
from app.infra.s3 import s3_client
from app.jobs.task_tracking import run_tracked_task

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def recompute_monthly_aggregates(self, org_id: str, correlation_id: str | None = None):
    return run_tracked_task(
        self,
        org_id=org_id,
        task_name="recompute_monthly_aggregates",
        dedupe_key=f"recompute-agg:{org_id}",
        payload={"org_id": org_id},
        correlation_id=correlation_id,
        max_retries=3,
        runner=lambda: _recompute_aggregates(org_id),
        result_payload_builder=lambda months: {"months_recomputed": months},
    )


async def _recompute_aggregates(org_id: str) -> int:
    async with SessionLocal() as db:
        svc = AnalyticsService(AnalyticsRepo(db))
        count = await svc.recompute_monthly_aggregates(uuid.UUID(org_id))
        await db.commit()
    logger.info("recompute_monthly_aggregates_done", org_id=org_id, months=count)
    return count


@shared_task(bind=True)
def recompute_forecasts(self, org_id: str, correlation_id: str | None = None):
    return run_tracked_task(
        self,
        org_id=org_id,
        task_name="recompute_forecasts",
        dedupe_key=f"recompute-forecast:{org_id}",
        payload={"org_id": org_id},
        correlation_id=correlation_id,
        max_retries=3,
        runner=lambda: _recompute_forecasts(org_id),
        result_payload_builder=lambda rows: {"rows": rows},
    )


async def _recompute_forecasts(org_id: str) -> int:
    async with SessionLocal() as db:
        svc = ForecastService(ForecastRepo(db), AnalyticsRepo(db))
        count = await svc.recompute(uuid.UUID(org_id), months=6)
        await db.commit()
    logger.info("recompute_forecasts_done", org_id=org_id, rows=count)
    return count


@shared_task(bind=True)
def recompute_alerts(self, org_id: str, correlation_id: str | None = None):
    return run_tracked_task(
        self,
        org_id=org_id,
        task_name="recompute_alerts",
        dedupe_key=f"recompute-alerts:{org_id}",
        payload={"org_id": org_id},
        correlation_id=correlation_id,
        max_retries=3,
        runner=lambda: _recompute_alerts(org_id),
        result_payload_builder=lambda created: {"created_alerts": created},
    )


async def _recompute_alerts(org_id: str) -> int:
    org_uuid = uuid.UUID(org_id)
    async with SessionLocal() as db:
        svc = AlertsService(db, AlertRepo(db))
        created = await svc.recompute(org_uuid)
        await db.commit()
    logger.info("recompute_alerts_done", org_id=org_id, created=created)
    return created


@shared_task(bind=True)
def verify_report_objects(self, org_id: str, correlation_id: str | None = None):
    return run_tracked_task(
        self,
        org_id=org_id,
        task_name="verify_report_objects",
        dedupe_key=f"verify-reports:{org_id}",
        payload={"org_id": org_id},
        correlation_id=correlation_id,
        max_retries=3,
        runner=lambda: _verify_report_objects(org_id),
        result_payload_builder=lambda result: result,
    )


async def _verify_report_objects(org_id: str) -> dict:
    org_uuid = uuid.UUID(org_id)
    missing = 0
    checked = 0
    s3 = s3_client()
    bucket = get_settings().minio_bucket
    async with SessionLocal() as db:
        reports = await ReportRepo(db).list_reports(org_uuid)
        for report in reports:
            checked += 1
            try:
                s3.head_object(Bucket=bucket, Key=report.file_key)
            except Exception:
                missing += 1
    logger.info("verify_report_objects_done", org_id=org_id, checked=checked, missing=missing)
    return {"checked": checked, "missing": missing}
