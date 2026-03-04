from celery.schedules import crontab

from app.jobs.celery_app import celery_app

celery_app.conf.beat_schedule = {
    "weekly-reports": {
        "task": "app.jobs.tasks.reports.generate_all_org_reports",
        "schedule": crontab(minute=0, hour=1, day_of_week="mon"),
    }
}
