from importlib import reload

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient


def _load_handlers(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.main as main_mod

    return reload(main_mod)


def test_http_error_uses_standard_envelope(monkeypatch):
    main_mod = _load_handlers(monkeypatch)
    app = FastAPI()
    app.add_exception_handler(HTTPException, main_mod.http_exception_handler)

    @app.get("/boom")
    async def boom():
        raise HTTPException(status_code=403, detail="Forbidden")

    client = TestClient(app)
    res = client.get("/boom", headers={"X-Request-ID": "req-123"})
    assert res.status_code == 403
    body = res.json()
    assert body["code"] == "forbidden"
    assert body["message"] == "Forbidden"
    assert body["detail"] == "Forbidden"
    assert "request_id" in body


def test_validation_error_uses_standard_envelope(monkeypatch):
    main_mod = _load_handlers(monkeypatch)
    app = FastAPI()
    app.add_exception_handler(RequestValidationError, main_mod.validation_exception_handler)

    @app.get("/needs-int")
    async def needs_int(v: int):
        return {"v": v}

    client = TestClient(app)
    res = client.get("/needs-int?v=abc")
    assert res.status_code == 422
    body = res.json()
    assert body["code"] == "validation_error"
    assert body["message"] == "Validation failed"
    assert isinstance(body["detail"], list)
