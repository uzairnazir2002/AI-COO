import uuid
from types import SimpleNamespace

import pytest

from app.domain.services.workforce_announcement_service import WorkforceAnnouncementService


def test_visible_org_all_without_employee():
    row = SimpleNamespace(audience_kind="ORG_ALL", audience_ids=None)
    assert WorkforceAnnouncementService._visible_to_member(row, user_email="a@b.com", emp=None) is True


def test_department_audience_requires_employee_match():
    did = uuid.uuid4()
    row = SimpleNamespace(audience_kind="DEPARTMENT", audience_ids=[str(did)])
    assert WorkforceAnnouncementService._visible_to_member(row, user_email="a@b.com", emp=None) is False


def test_department_audience_visible_when_department_matches():
    did = uuid.uuid4()
    row = SimpleNamespace(audience_kind="DEPARTMENT", audience_ids=[str(did)])
    emp = SimpleNamespace(department_id=did, location_id=None, title_id=None, manager_employee_id=None)
    assert WorkforceAnnouncementService._visible_to_member(row, user_email="a@b.com", emp=emp) is True


def test_manager_team_visible_when_manager_matches():
    mid = uuid.uuid4()
    row = SimpleNamespace(audience_kind="MANAGER_TEAM", audience_ids=[str(mid)])
    emp = SimpleNamespace(department_id=None, location_id=None, title_id=None, manager_employee_id=mid)
    assert WorkforceAnnouncementService._visible_to_member(row, user_email="a@b.com", emp=emp) is True


@pytest.mark.asyncio
async def test_validate_audience_targeted_requires_ids():
    svc = WorkforceAnnouncementService(
        repo=None,  # type: ignore[arg-type]
        employee_repo=None,  # type: ignore[arg-type]
        org_repo=None,  # type: ignore[arg-type]
        outbox_repo=None,  # type: ignore[arg-type]
        delivery_repo=None,  # type: ignore[arg-type]
        template_repo=None,  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="audience_ids"):
        svc._validate_audience(kind="DEPARTMENT", ids=[])
