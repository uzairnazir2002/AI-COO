import traceback
import uuid

from celery import Task
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.db.session import SessionLocal
from app.domain.repos.dead_letter_repo import DeadLetterRepo
from app.domain.repos.job_repo import JobRepo
from app.jobs.async_runtime import run_async


def _traceback_summary(exc: Exception) -> str:
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return tb[:2000]


def _request_header(task: Task, key: str) -> str | None:
    headers = getattr(task.request, "headers", None) or {}
    if isinstance(headers, dict):
        for k, v in headers.items():
            if str(k).lower() == key.lower():
                return str(v)
    return None


def _task_id(task: Task) -> str:
    return str(getattr(task.request, "id", None) or uuid.uuid4())


async def mark_running(
    *,
    task_id: str,
    request_id: str | None,
    org_id: str | None,
    task_name: str,
    dedupe_key: str,
    payload: dict,
    correlation_id: str | None,
) -> str:
    async with SessionLocal() as db:
        repo = JobRepo(db)
        state = await repo.upsert_running(
            task_id=task_id,
            task_name=task_name,
            dedupe_key=dedupe_key,
            payload=payload,
            org_id=uuid.UUID(org_id) if org_id else None,
            request_id=request_id,
            correlation_id=correlation_id,
        )
        await db.commit()
    return state.task_id


async def mark_succeeded(task_id: str, result: dict | None = None) -> None:
    async with SessionLocal() as db:
        await JobRepo(db).mark_succeeded(task_id, result)
        await db.commit()


async def mark_retrying(task_id: str, *, retry_count: int, error: Exception) -> None:
    async with SessionLocal() as db:
        await JobRepo(db).mark_retrying(
            task_id,
            retry_count=retry_count,
            error=str(error),
            traceback_summary=_traceback_summary(error),
        )
        await db.commit()


async def mark_failed(task_id: str, *, retry_count: int, error: Exception) -> None:
    async with SessionLocal() as db:
        repo = JobRepo(db)
        await repo.mark_failed(
            task_id,
            retry_count=retry_count,
            error=str(error),
            traceback_summary=_traceback_summary(error),
        )
        state = await repo.by_task_id(task_id)
        if state:
            await DeadLetterRepo(db).record_failure(
                org_id=state.org_id,
                source_type="JOB",
                source_id=state.id,
                source_task_id=task_id,
                source_name=state.task_name,
                attempts=max(int(retry_count or 0), 1),
                last_error=str(error),
                payload=state.payload or {},
                metadata_json={"dedupe_key": state.dedupe_key},
            )
        await db.commit()


def run_tracked_task(
    task: Task,
    *,
    org_id: str | None,
    task_name: str,
    dedupe_key: str,
    payload: dict,
    correlation_id: str | None,
    max_retries: int,
    runner,
    result_payload_builder,
):
    requested_task_id = _task_id(task)
    request_id = _request_header(task, "x-request-id")
    task_id = run_async(
        mark_running(
            task_id=requested_task_id,
            request_id=request_id,
            org_id=org_id,
            task_name=task_name,
            dedupe_key=dedupe_key,
            payload=payload,
            correlation_id=correlation_id,
        )
    )
    clear_contextvars()
    bind_contextvars(task_id=task_id, task_name=task_name, correlation_id=correlation_id, request_id=request_id)
    try:
        result = run_async(runner())
    except Exception as exc:
        retries = int(getattr(task.request, "retries", 0))
        if retries < max_retries:
            run_async(mark_retrying(task_id, retry_count=retries + 1, error=exc))
            clear_contextvars()
            raise task.retry(exc=exc, countdown=2 ** retries)
        run_async(mark_failed(task_id, retry_count=retries, error=exc))
        clear_contextvars()
        raise

    run_async(mark_succeeded(task_id, result_payload_builder(result)))
    clear_contextvars()
    return result
