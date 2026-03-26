from datetime import timedelta

from app.core.security import create_token


def test_create_token_has_unique_jti_per_mint():
    t1 = create_token("user-1", "refresh", timedelta(days=1))
    t2 = create_token("user-1", "refresh", timedelta(days=1))

    assert t1 != t2
