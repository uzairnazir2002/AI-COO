from importlib import reload


def test_celery_registers_alerts_forecasts_outbox_tasks(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    import app.jobs.celery_app as celery_app_module

    module = reload(celery_app_module)
    tasks = module.celery_app.tasks

    assert "app.jobs.tasks.analytics.recompute_org_analytics" in tasks
    assert "app.jobs.tasks.alerts.recalc_alerts" in tasks
    assert "app.jobs.tasks.forecasts.recalc_forecasts" in tasks
    assert "app.jobs.tasks.outbox.process_outbox" in tasks
    assert "app.jobs.tasks.privacy.purge_deletion_requests" in tasks
