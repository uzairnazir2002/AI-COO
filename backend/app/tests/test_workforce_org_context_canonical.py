from types import SimpleNamespace
import uuid

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.deps import resolve_workforce_org_id_from_request
from app.domain.repos.org_repo import OrgRepo


class _FakeDb:
    async def execute(self, *_args, **_kwargs):
        return None


def _request_with_header(org_id: str | None) -> Request:
    headers = []
    if org_id is not None:
        headers.append((b"x-org-id", org_id.encode("utf-8")))
    scope = {"type": "http", "headers": headers, "query_string": b""}
    return Request(scope)


@pytest.mark.asyncio
async def test_workforce_org_context_allows_fallback_when_flag_disabled(monkeypatch):
    org_id = uuid.uuid4()

    async def fake_get_settings(self, _org_id):
        return SimpleNamespace(workforce_org_context_canonical=False)

    monkeypatch.setattr(OrgRepo, "get_settings", fake_get_settings)
    resolved = await resolve_workforce_org_id_from_request(org_id, _request_with_header(None), _FakeDb())
    assert resolved == org_id


@pytest.mark.asyncio
async def test_workforce_org_context_requires_header_when_flag_enabled(monkeypatch):
    org_id = uuid.uuid4()

    async def fake_get_settings(self, _org_id):
        return SimpleNamespace(workforce_org_context_canonical=True)

    monkeypatch.setattr(OrgRepo, "get_settings", fake_get_settings)
    with pytest.raises(HTTPException) as exc:
        await resolve_workforce_org_id_from_request(org_id, _request_with_header(None), _FakeDb())
    assert exc.value.status_code == 422
    assert exc.value.detail == "X-Org-Id header is required"


@pytest.mark.asyncio
async def test_workforce_org_context_accepts_matching_header_when_flag_enabled(monkeypatch):
    org_id = uuid.uuid4()

    async def fake_get_settings(self, _org_id):
        return SimpleNamespace(workforce_org_context_canonical=True)

    monkeypatch.setattr(OrgRepo, "get_settings", fake_get_settings)
    resolved = await resolve_workforce_org_id_from_request(org_id, _request_with_header(str(org_id)), _FakeDb())
    assert resolved == org_id
