import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def transactions_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from importlib import reload
    import app.api.v1.transactions as transactions

    return reload(transactions)


def _app_with_overrides(monkeypatch, module):
    app = FastAPI()
    app.include_router(module.router, prefix="/api/v1/transactions")

    async def fake_user():
        return SimpleNamespace(id=uuid.uuid4(), email="u@example.com")

    async def fake_db():
        yield object()

    async def fake_ctx(org_id: uuid.UUID, user=None, db=None):
        return SimpleNamespace(org_id=org_id, role="OWNER")

    app.dependency_overrides[module.get_current_user] = fake_user
    app.dependency_overrides[module.get_db] = fake_db
    monkeypatch.setattr(module, "get_org_context", fake_ctx)
    return app


def test_import_history_list_and_error_download(monkeypatch, transactions_module):
    org_id = uuid.uuid4()
    import_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    class _Repo:
        def __init__(self, _db):
            pass

        async def list_imports(self, _org_id, page, page_size):
            return (
                [
                    SimpleNamespace(
                        id=import_id,
                        file_name="tx.csv",
                        status="COMPLETED",
                        total_rows=10,
                        inserted_count=8,
                        duplicate_count=2,
                        error_count=2,
                        mapping_profile_id=None,
                        created_at=now,
                        created_by=uuid.uuid4(),
                    )
                ],
                1,
            )

        async def get(self, _import_id, _org_id):
            return SimpleNamespace(
                id=import_id,
                error_rows_json=[{"row": 2, "reason": "duplicate_existing", "data": {"amount": "10"}}],
            )

    monkeypatch.setattr(transactions_module, "ImportRepo", _Repo)
    app = _app_with_overrides(monkeypatch, transactions_module)
    client = TestClient(app)

    list_res = client.get(f"/api/v1/transactions/imports?org_id={org_id}&page=1&page_size=20")
    assert list_res.status_code == 200
    body = list_res.json()
    assert body["total"] == 1
    assert body["items"][0]["file_name"] == "tx.csv"

    err_res = client.get(f"/api/v1/transactions/imports/{import_id}/errors?org_id={org_id}")
    assert err_res.status_code == 200
    assert "row,reason,data" in err_res.text
    assert "duplicate_existing" in err_res.text
