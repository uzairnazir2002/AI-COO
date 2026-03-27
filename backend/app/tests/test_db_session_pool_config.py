from importlib import reload


def test_db_engine_uses_configured_pool_settings(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("DB_POOL_SIZE", "7")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "3")
    monkeypatch.setenv("DB_POOL_TIMEOUT_SECONDS", "11")
    monkeypatch.setenv("DB_POOL_RECYCLE_SECONDS", "222")
    monkeypatch.setenv("API_DB_POOL_SIZE", "7")
    monkeypatch.setenv("API_DB_MAX_OVERFLOW", "3")
    monkeypatch.setenv("API_DB_POOL_TIMEOUT_SECONDS", "11")
    monkeypatch.setenv("API_DB_POOL_RECYCLE_SECONDS", "222")
    monkeypatch.setenv("APP_ROLE", "api")

    captured: dict = {}

    def fake_create_async_engine(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return object()

    def fake_async_sessionmaker(*args, **kwargs):
        captured["sessionmaker_args"] = args
        captured["sessionmaker_kwargs"] = kwargs
        return object()

    monkeypatch.setattr("sqlalchemy.ext.asyncio.create_async_engine", fake_create_async_engine)
    monkeypatch.setattr("sqlalchemy.ext.asyncio.async_sessionmaker", fake_async_sessionmaker)
    from app.core.config import get_settings

    get_settings.cache_clear()

    import app.db.session as session_module

    reload(session_module)

    assert captured["url"] == "postgresql+asyncpg://u:p@localhost:5432/db"
    assert captured["kwargs"]["pool_size"] == 7
    assert captured["kwargs"]["max_overflow"] == 3
    assert captured["kwargs"]["pool_timeout"] == 11
    assert captured["kwargs"]["pool_recycle"] == 222
    assert captured["kwargs"]["pool_use_lifo"] is True


def test_db_engine_uses_worker_pool_overrides(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("DB_POOL_SIZE", "7")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "3")
    monkeypatch.setenv("DB_POOL_TIMEOUT_SECONDS", "11")
    monkeypatch.setenv("DB_POOL_RECYCLE_SECONDS", "222")
    monkeypatch.setenv("WORKER_DB_POOL_SIZE", "2")
    monkeypatch.setenv("WORKER_DB_MAX_OVERFLOW", "0")
    monkeypatch.setenv("WORKER_DB_POOL_TIMEOUT_SECONDS", "9")
    monkeypatch.setenv("WORKER_DB_POOL_RECYCLE_SECONDS", "60")
    monkeypatch.setenv("APP_ROLE", "worker")

    captured: dict = {}

    def fake_create_async_engine(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return object()

    def fake_async_sessionmaker(*args, **kwargs):
        captured["sessionmaker_args"] = args
        captured["sessionmaker_kwargs"] = kwargs
        return object()

    monkeypatch.setattr("sqlalchemy.ext.asyncio.create_async_engine", fake_create_async_engine)
    monkeypatch.setattr("sqlalchemy.ext.asyncio.async_sessionmaker", fake_async_sessionmaker)
    from app.core.config import get_settings

    get_settings.cache_clear()

    import app.db.session as session_module

    reload(session_module)

    assert captured["url"] == "postgresql+asyncpg://u:p@localhost:5432/db"
    assert captured["kwargs"]["pool_size"] == 2
    assert captured["kwargs"]["max_overflow"] == 0
    assert captured["kwargs"]["pool_timeout"] == 9
    assert captured["kwargs"]["pool_recycle"] == 60
    assert captured["kwargs"]["pool_use_lifo"] is True
