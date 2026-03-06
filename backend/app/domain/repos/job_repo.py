import uuid

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.job_state import JobState
from app.utils.time import utc_now


class JobRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_running(
        self,
        *,
        task_id: str,
        task_name: str,
        dedupe_key: str,
        payload: dict,
        org_id: uuid.UUID | None,
        request_id: str | None,
        correlation_id: str | None,
    ) -> JobState:
        state = await self.db.scalar(select(JobState).where(JobState.task_id == task_id))
        if not state:
            state = JobState(
                task_id=task_id,
                task_name=task_name,
                job_name=task_name,
                dedupe_key=dedupe_key,
                payload=payload,
                org_id=org_id,
                request_id=request_id,
                correlation_id=correlation_id,
                status="RUNNING",
                progress=0,
                retry_count=0,
            )
            self.db.add(state)
            await self.db.flush()
            return state

        state.status = "RUNNING"
        state.task_name = task_name
        state.job_name = task_name
        state.dedupe_key = dedupe_key
        state.payload = payload
        state.org_id = org_id
        state.request_id = request_id
        state.correlation_id = correlation_id
        state.last_error = None
        state.traceback_summary = None
        state.updated_at = utc_now()
        await self.db.flush()
        return state

    async def mark_retrying(self, task_id: str, *, retry_count: int, error: str, traceback_summary: str | None) -> None:
        state = await self.db.scalar(select(JobState).where(JobState.task_id == task_id))
        if not state:
            return
        state.status = "RETRYING"
        state.retry_count = retry_count
        state.last_error = error
        state.traceback_summary = traceback_summary
        state.last_retry_at = utc_now()
        state.updated_at = utc_now()
        await self.db.flush()

    async def mark_failed(self, task_id: str, *, retry_count: int, error: str, traceback_summary: str | None) -> None:
        state = await self.db.scalar(select(JobState).where(JobState.task_id == task_id))
        if not state:
            return
        state.status = "FAILED"
        state.retry_count = retry_count
        state.last_error = error
        state.traceback_summary = traceback_summary
        state.updated_at = utc_now()
        await self.db.flush()

    async def mark_succeeded(self, task_id: str, result: dict | None = None) -> None:
        state = await self.db.scalar(select(JobState).where(JobState.task_id == task_id))
        if not state:
            return
        state.status = "SUCCEEDED"
        state.progress = 100
        state.result = result or {}
        state.updated_at = utc_now()
        await self.db.flush()

    async def mark_cancelled(self, task_id: str, *, error: str | None = None) -> None:
        state = await self.db.scalar(select(JobState).where(JobState.task_id == task_id))
        if not state:
            return
        state.status = "CANCELLED"
        state.last_error = error
        state.updated_at = utc_now()
        await self.db.flush()

    async def list_jobs(
        self,
        *,
        org_id: uuid.UUID,
        status: str | None,
        task_name: str | None,
        since: datetime | None,
        until: datetime | None,
        page: int,
        page_size: int,
    ) -> tuple[list[JobState], int]:
        stmt = select(JobState).where(JobState.org_id == org_id)
        count_stmt = select(func.count()).select_from(JobState).where(JobState.org_id == org_id)

        if status:
            stmt = stmt.where(JobState.status == status)
            count_stmt = count_stmt.where(JobState.status == status)
        if task_name:
            stmt = stmt.where(JobState.task_name == task_name)
            count_stmt = count_stmt.where(JobState.task_name == task_name)
        if since:
            stmt = stmt.where(JobState.created_at >= since)
            count_stmt = count_stmt.where(JobState.created_at >= since)
        if until:
            stmt = stmt.where(JobState.created_at <= until)
            count_stmt = count_stmt.where(JobState.created_at <= until)

        stmt = stmt.order_by(JobState.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = int((await self.db.execute(count_stmt)).scalar_one())
        return items, total

    async def list_system_jobs(
        self,
        *,
        task_name: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[JobState], int]:
        stmt = select(JobState).where(JobState.org_id.is_(None))
        count_stmt = select(func.count()).select_from(JobState).where(JobState.org_id.is_(None))

        if task_name:
            stmt = stmt.where(JobState.task_name == task_name)
            count_stmt = count_stmt.where(JobState.task_name == task_name)

        stmt = stmt.order_by(JobState.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = int((await self.db.execute(count_stmt)).scalar_one())
        return items, total

    async def by_id(self, job_id: uuid.UUID) -> JobState | None:
        return await self.db.scalar(select(JobState).where(JobState.id == job_id))
