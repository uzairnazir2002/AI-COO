from app.domain.models.job_state import JobState
from app.jobs.tasks.admin import recompute_alerts, recompute_forecasts, recompute_monthly_aggregates, verify_report_objects
from app.jobs.tasks.banks import sync_bank_connection, sync_all_active_bank_connections
from app.jobs.tasks.reports import generate_weekly_report


def retry_job_task(job: JobState):
    payload = job.payload or {}
    if job.task_name == "recompute_monthly_aggregates":
        return recompute_monthly_aggregates.apply_async(args=[payload["org_id"], job.correlation_id])
    if job.task_name == "recompute_forecasts":
        return recompute_forecasts.apply_async(args=[payload["org_id"], job.correlation_id])
    if job.task_name == "recompute_alerts":
        return recompute_alerts.apply_async(args=[payload["org_id"], job.correlation_id])
    if job.task_name == "verify_report_objects":
        return verify_report_objects.apply_async(args=[payload["org_id"], job.correlation_id])
    if job.task_name == "generate_weekly_report":
        return generate_weekly_report.apply_async(
            args=[payload["org_id"], payload["week_start"], payload.get("created_by"), job.correlation_id]
        )
    if job.task_name == "sync_bank_connection":
        return sync_bank_connection.apply_async(
            args=[payload["org_id"], payload["connection_id"], payload.get("triggered_by_user_id"), job.correlation_id]
        )
    if job.task_name == "sync_all_active_bank_connections":
        return sync_all_active_bank_connections.apply_async(args=[job.correlation_id])
    return None
