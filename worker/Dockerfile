FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend /app
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

CMD ["celery", "-A", "app.jobs.celery_app.celery_app", "worker", "--loglevel=INFO"]
