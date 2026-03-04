# Worker Service

Celery worker/beat runtime for asynchronous analytics tasks.

## Responsibilities
- `generate_weekly_report`
- `send_email_task`
- `recalc_forecasts`
- Weekly scheduled trigger via Celery Beat

## Local usage
- Worker: `celery -A app.jobs.celery_app.celery_app worker --loglevel=INFO`
- Beat: `celery -A app.jobs.celery_app.celery_app beat --loglevel=INFO`
