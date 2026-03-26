import uuid
from types import SimpleNamespace

import pytest

from app.domain.services.errors import NotFoundError
from app.domain.services.location_service import LocationService


class _FakeLocationRepo:
    def __init__(self):
        self.by_id: dict[tuple[uuid.UUID, uuid.UUID], SimpleNamespace] = {}
        self.existing: SimpleNamespace | None = None
        self.created: list[SimpleNamespace] = []

    async def list_by_org(self, org_id, *, include_inactive=False):
        _ = (org_id, include_inactive)
        return []

    async def get_by_id(self, location_id, org_id):
        return self.by_id.get((location_id, org_id))

    async def get_by_name_or_code(self, **_kwargs):
        return self.existing

    async def create(self, location):
        self.created.append(location)
        return location


@pytest.mark.asyncio
async def test_create_location_rejects_duplicate():
    repo = _FakeLocationRepo()
    repo.existing = SimpleNamespace(id=uuid.uuid4())
    svc = LocationService(repo)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="already exists"):
        await svc.create_location(
            org_id=uuid.uuid4(),
            actor_user_id=uuid.uuid4(),
            name="HQ",
            code="HQ",
            is_active=True,
        )


@pytest.mark.asyncio
async def test_ensure_org_location_rejects_inactive():
    repo = _FakeLocationRepo()
    org_id = uuid.uuid4()
    location_id = uuid.uuid4()
    repo.by_id[(location_id, org_id)] = SimpleNamespace(id=location_id, org_id=org_id, is_active=False)
    svc = LocationService(repo)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="inactive"):
        await svc.ensure_org_location(org_id=org_id, location_id=location_id)


@pytest.mark.asyncio
async def test_update_location_not_found():
    repo = _FakeLocationRepo()
    svc = LocationService(repo)  # type: ignore[arg-type]
    with pytest.raises(NotFoundError):
        await svc.update_location(
            org_id=uuid.uuid4(),
            location_id=uuid.uuid4(),
            name="North",
            code=None,
            is_active=True,
        )
