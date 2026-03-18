import io
import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


@pytest.fixture
def transactions_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from importlib import reload
    import app.api.v1.transactions as transactions

    return reload(transactions)


class _FakeDb:
    async def commit(self):
        return None


class _ProfileStore:
    def __init__(self):
        self.rows = {}


class _FakeImportProfileService:
    def __init__(self, _repo):
        self.store = _PROFILE_STORE

    async def list_profiles(self, org_id, user_id):
        return [r for r in self.store.rows.values() if r.org_id == org_id and (r.user_id is None or r.user_id == user_id)]

    async def create_profile(self, org_id, actor_user_id, name, column_map, shared):
        pid = uuid.uuid4()
        row = SimpleNamespace(
            id=pid,
            org_id=org_id,
            user_id=None if shared else actor_user_id,
            name=name,
            column_map=column_map,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.store.rows[pid] = row
        return row

    async def update_profile(self, profile_id, org_id, actor_user_id, name, column_map, shared):
        row = self.store.rows.get(profile_id)
        if not row or row.org_id != org_id:
            raise HTTPException(status_code=404, detail="Import mapping profile not found")
        if row.user_id and row.user_id != actor_user_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        if name is not None:
            row.name = name
        if column_map is not None:
            row.column_map = column_map
        if shared is not None:
            row.user_id = None if shared else actor_user_id
        row.updated_at = datetime.now(timezone.utc)
        return row

    async def delete_profile(self, profile_id, org_id, actor_user_id):
        row = self.store.rows.get(profile_id)
        if not row or row.org_id != org_id:
            raise HTTPException(status_code=404, detail="Import mapping profile not found")
        if row.user_id and row.user_id != actor_user_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        self.store.rows.pop(profile_id, None)

    async def resolve_import_mapping(self, org_id, actor_user_id, mapping, profile_id):
        if mapping:
            return mapping, profile_id
        row = self.store.rows.get(profile_id)
        if not row or row.org_id != org_id:
            from app.domain.services.errors import NotFoundError

            raise NotFoundError("Mapping profile not found")
        if row.user_id and row.user_id != actor_user_id:
            from app.domain.services.errors import ForbiddenError

            raise ForbiddenError("Forbidden")
        return row.column_map, row.id


class _FakeTransactionService:
    def __init__(self, *_args, **_kwargs):
        self.calls = []

    async def import_csv(self, user_id, org_id, content, mapping, file_name, mapping_profile_id=None):
        _ = (user_id, content, file_name)
        self.calls.append({"org_id": org_id, "mapping": mapping, "mapping_profile_id": mapping_profile_id})
        return str(uuid.uuid4()), {"rows": 1, "detected_duplicates": 0}, 1

    async def preview_csv(self, user_id, org_id, content, mapping, file_name, mapping_profile_id=None):
        _ = (user_id, content, file_name)
        self.calls.append({"org_id": org_id, "mapping": mapping, "mapping_profile_id": mapping_profile_id})
        return str(uuid.uuid4()), {"rows": 1, "detected_duplicates": 0}


class _FakeAuditRepo:
    def __init__(self, _db):
        pass

    async def log(self, *args, **kwargs):
        _ = (args, kwargs)


class _FakeImportRepo:
    def __init__(self, _db):
        pass


class _FakePlanRepo:
    def __init__(self, _db):
        pass


class _FakeUsageService:
    def __init__(self, _repo):
        pass


def _app(monkeypatch, module, role="OWNER"):
    app = FastAPI()
    app.include_router(module.router, prefix="/api/v1/transactions")

    user = SimpleNamespace(id=uuid.uuid4(), email="owner@example.com")

    async def fake_user():
        return user

    async def fake_db():
        yield _FakeDb()

    async def fake_ctx(org_id: uuid.UUID, user=None, db=None):
        _ = (user, db)
        return SimpleNamespace(org_id=org_id, role=role)

    app.dependency_overrides[module.get_current_user] = fake_user
    app.dependency_overrides[module.get_db] = fake_db

    from app.api import deps as shared_deps

    app.dependency_overrides[shared_deps.get_org_context] = fake_ctx
    monkeypatch.setattr(module, "get_org_context", fake_ctx)
    monkeypatch.setattr(module, "ImportProfileService", _FakeImportProfileService)
    monkeypatch.setattr(module, "ImportProfileRepo", lambda _db: object())
    monkeypatch.setattr(module, "AuditRepo", _FakeAuditRepo)
    monkeypatch.setattr(module, "ImportRepo", _FakeImportRepo)
    monkeypatch.setattr(module, "PlanRepo", _FakePlanRepo)
    monkeypatch.setattr(module, "UsageService", _FakeUsageService)
    return app, user


_PROFILE_STORE = _ProfileStore()


def test_import_profile_crud_and_list(monkeypatch, transactions_module):
    _PROFILE_STORE.rows.clear()
    app, user = _app(monkeypatch, transactions_module)
    client = TestClient(app)
    org_id = str(uuid.uuid4())

    create = client.post(
        "/api/v1/transactions/import-profiles",
        json={
            "org_id": org_id,
            "name": "Bank CSV",
            "column_map": {"date": "Date", "amount": "Amount", "type": "Type", "category": "Category"},
            "shared": False,
        },
    )
    assert create.status_code == 200, create.text
    profile_id = create.json()["id"]
    assert create.json()["user_id"] == str(user.id)

    listing = client.get(f"/api/v1/transactions/import-profiles?org_id={org_id}")
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    update = client.put(
        f"/api/v1/transactions/import-profiles/{profile_id}",
        json={"org_id": org_id, "name": "Bank CSV v2", "shared": True},
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Bank CSV v2"
    assert update.json()["user_id"] is None

    delete = client.delete(f"/api/v1/transactions/import-profiles/{profile_id}?org_id={org_id}")
    assert delete.status_code == 200
    assert delete.json()["ok"] is True


def test_import_profile_mutation_forbidden_for_viewer(monkeypatch, transactions_module):
    _PROFILE_STORE.rows.clear()
    app, _user = _app(monkeypatch, transactions_module, role="VIEWER")
    client = TestClient(app)
    org_id = str(uuid.uuid4())

    create = client.post(
        "/api/v1/transactions/import-profiles",
        json={"org_id": org_id, "name": "x", "column_map": {"date": "date", "amount": "amount", "type": "type", "category": "category"}, "shared": False},
    )
    assert create.status_code == 403


def test_import_csv_uses_saved_profile_mapping(monkeypatch, transactions_module):
    _PROFILE_STORE.rows.clear()
    app, user = _app(monkeypatch, transactions_module)
    client = TestClient(app)
    org_id = uuid.uuid4()

    profile = SimpleNamespace(
        id=uuid.uuid4(),
        org_id=org_id,
        user_id=user.id,
        name="saved",
        column_map={"date": "date", "amount": "amount", "type": "type", "category": "category", "vendor": "vendor", "notes": "notes"},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    _PROFILE_STORE.rows[profile.id] = profile

    fake_tx_service = _FakeTransactionService()
    monkeypatch.setattr(transactions_module, "TransactionService", lambda *args, **kwargs: fake_tx_service)

    csv_content = "date,amount,type,category,vendor,notes\n2026-03-10,100.00,EXPENSE,Ops,Acme,ok\n"
    files = {"file": ("demo.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    data = {
        "org_id": str(org_id),
        "profile_id": str(profile.id),
        "commit": "true",
    }

    res = client.post("/api/v1/transactions/import/csv", data=data, files=files)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["mapping_profile_id"] == str(profile.id)
    assert len(fake_tx_service.calls) == 1
    assert fake_tx_service.calls[0]["mapping_profile_id"] == profile.id
    assert fake_tx_service.calls[0]["mapping"]["date"] == "date"


def test_import_csv_profile_tenant_isolation(monkeypatch, transactions_module):
    _PROFILE_STORE.rows.clear()
    app, user = _app(monkeypatch, transactions_module)
    client = TestClient(app)
    org_id = uuid.uuid4()
    other_org = uuid.uuid4()

    profile = SimpleNamespace(
        id=uuid.uuid4(),
        org_id=other_org,
        user_id=user.id,
        name="other-org-profile",
        column_map={"date": "date", "amount": "amount", "type": "type", "category": "category"},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    _PROFILE_STORE.rows[profile.id] = profile

    fake_tx_service = _FakeTransactionService()
    monkeypatch.setattr(transactions_module, "TransactionService", lambda *args, **kwargs: fake_tx_service)

    csv_content = "date,amount,type,category\\n2026-03-10,100.00,EXPENSE,Ops\\n"
    files = {"file": ("demo.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    data = {
        "org_id": str(org_id),
        "profile_id": str(profile.id),
        "commit": "true",
    }

    res = client.post("/api/v1/transactions/import/csv", data=data, files=files)
    assert res.status_code == 404
