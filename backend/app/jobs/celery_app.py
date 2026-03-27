from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings
from app.core.observability import init_sentry

settings = get_settings()
init_sentry(settings, service_name="celery-worker")
TASK_MODULES = [
    "app.jobs.tasks.admin",
    "app.jobs.tasks.analytics",
    "app.jobs.tasks.alerts",
    "app.jobs.tasks.emails",
    "app.jobs.tasks.forecasts",
    "app.jobs.tasks.outbox",
    "app.jobs.tasks.banks",
    "app.jobs.tasks.privacy",
    "app.jobs.tasks.reports",
]

celery_app = Celery("ai_coo", broker=settings.redis_url, backend=settings.redis_url, include=TASK_MODULES)
celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "weekly-reports": {
            "task": "app.jobs.tasks.reports.generate_all_org_reports",
            "schedule": crontab(minute=0, hour=1, day_of_week="mon"),
        },
        "outbox-consumer": {
            "task": "app.jobs.tasks.outbox.process_outbox",
            "schedule": crontab(minute="*"),
        },
        "deletion-purge": {
            "task": "app.jobs.tasks.privacy.purge_deletion_requests",
            "schedule": crontab(minute=30, hour=2),
        },
        "bank-sync-active-connections": {
            "task": "app.jobs.tasks.banks.sync_all_active_bank_connections",
            "schedule": crontab(minute="*/30"),
        },
    },
)
celery_app.set_default()
# Import task modules explicitly so shared_task decorators bind to this app.
from app.jobs import tasks as _registered_tasks  # noqa: F401,E402

celery_app.autodiscover_tasks(["app.jobs.tasks"])
