from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings
from app.core.observability import init_sentry

settings = get_settings()
init_sentry(settings, service_name="celery-worker")
celery_app = Celery("ai_coo", broker=settings.redis_url, backend=settings.redis_url)
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
    },
)
celery_app.autodiscover_tasks(["app.jobs.tasks"])
