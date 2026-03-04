import hashlib


from app.domain.services.auth_service import _h


def test_refresh_hashing_stable():
    t = "token"
    assert _h(t) == hashlib.sha256(t.encode("utf-8")).hexdigest()


def test_refresh_rotation_semantics():
    old = "old-refresh"
    new = "new-refresh"
    assert _h(old) != _h(new)
