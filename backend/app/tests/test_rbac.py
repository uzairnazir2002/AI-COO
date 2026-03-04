import pytest

from app.domain.services.org_service import require_role
from app.domain.services.errors import ForbiddenError


def test_viewer_cannot_edit():
    with pytest.raises(ForbiddenError):
        require_role("VIEWER", ["OWNER", "EDITOR"])


def test_owner_can_invite():
    require_role("OWNER", ["OWNER"])
