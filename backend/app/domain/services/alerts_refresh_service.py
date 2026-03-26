import uuid
from dataclasses import dataclass

from app.domain.repos.job_repo import JobRepo
from app.jobs.tasks.alerts import recalc_alerts


@dataclass(slots=True)
class AlertRecalcEnqueueResult:
    task_id: str
    status: str
    enqueued: bool


class AlertRefreshService:
    def __init__(self, job_repo: JobRepo):
        self.job_repo = job_repo

    async def enqueue_recalc(
        self,
        *,
        org_id: uuid.UUID,
        correlation_id: str | None = None,
        request_id: str | None = None,
        reason: str | None = None,
    ) -> AlertRecalcEnqueueResult:
        dedupe_key = f"alerts:{org_id}"
        existing = await self.job_repo.by_dedupe_key(dedupe_key, org_id)
        if existing and existing.status in {"PENDING", "RUNNING", "RETRYING"}:
            return AlertRecalcEnqueueResult(task_id=existing.task_id, status=existing.status, enqueued=False)

        headers = {"x-request-id": request_id} if request_id else None
        task = recalc_alerts.apply_async(args=[str(org_id), correlation_id], headers=headers)
        task_id = str(task.id)
        payload = {"org_id": str(org_id)}
        if reason:
            payload["reason"] = reason

        await self.job_repo.upsert_pending(
            task_id=task_id,
            task_name="recalc_alerts",
            dedupe_key=dedupe_key,
            payload=payload,
            org_id=org_id,
            request_id=request_id,
            correlation_id=correlation_id,
        )
        return AlertRecalcEnqueueResult(task_id=task_id, status="PENDING", enqueued=True)

