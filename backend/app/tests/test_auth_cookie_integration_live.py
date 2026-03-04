import os
import uuid

import httpx
import pytest


pytestmark = pytest.mark.integration


@pytest.mark.skipif(os.getenv("RUN_INTEGRATION_LIVE") != "1", reason="Set RUN_INTEGRATION_LIVE=1")
def test_cookie_auth_login_refresh_logout_flow():
    if os.getenv("AUTH_COOKIE_MODE", "false").lower() not in {"1", "true", "yes"}:
        pytest.skip("AUTH_COOKIE_MODE must be enabled for cookie auth integration test")

    base = os.getenv("INTEGRATION_BASE_URL", "http://localhost:8000/api/v1")
    email = f"cookie_it_{uuid.uuid4().hex[:12]}@example.com"
    password = "Password123!"

    with httpx.Client(timeout=30.0) as client:
        reg = client.post(f"{base}/auth/register", json={"email": email, "password": password})
        assert reg.status_code == 200, reg.text

        login = client.post(f"{base}/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200, login.text
        login_body = login.json()
        assert login_body.get("token_type") == "cookie"
        assert login_body.get("access_token") is None
        assert login_body.get("refresh_token") is None
        set_cookie_headers = login.headers.get_list("set-cookie")
        assert any("ai_coo_access_token=" in h for h in set_cookie_headers), "access cookie was not set"
        assert any("ai_coo_refresh_token=" in h for h in set_cookie_headers), "refresh cookie was not set"
        assert any("ai_coo_csrf_token=" in h for h in set_cookie_headers), "csrf cookie was not set"

        csrf = client.cookies.get("ai_coo_csrf_token")
        assert csrf, "csrf cookie missing from cookie jar"

        me = client.get(f"{base}/auth/me")
        assert me.status_code == 200, me.text
        assert me.json()["user"]["email"] == email

        # CSRF is required for mutating requests in cookie auth mode.
        refreshed_without_csrf = client.post(f"{base}/auth/refresh", json={})
        assert refreshed_without_csrf.status_code == 403, refreshed_without_csrf.text

        # In cookie mode, refresh endpoint can use cookie token with empty JSON body + csrf header.
        refreshed = client.post(f"{base}/auth/refresh", json={}, headers={"X-CSRF-Token": csrf})
        assert refreshed.status_code == 200, refreshed.text
        refreshed_body = refreshed.json()
        assert refreshed_body.get("token_type") == "cookie"
        assert refreshed_body.get("access_token") is None
        assert refreshed_body.get("refresh_token") is None
        refreshed_set_cookie = refreshed.headers.get_list("set-cookie")
        assert any("ai_coo_access_token=" in h for h in refreshed_set_cookie)
        assert any("ai_coo_refresh_token=" in h for h in refreshed_set_cookie)
        assert any("ai_coo_csrf_token=" in h for h in refreshed_set_cookie)
        csrf = client.cookies.get("ai_coo_csrf_token")
        assert csrf, "csrf cookie missing after refresh"

        create_org_without_csrf = client.post(f"{base}/organizations", json={"name": "Cookie Org"})
        assert create_org_without_csrf.status_code == 403, create_org_without_csrf.text
        create_org = client.post(f"{base}/organizations", json={"name": "Cookie Org"}, headers={"X-CSRF-Token": csrf})
        assert create_org.status_code == 200, create_org.text

        logout_without_csrf = client.post(f"{base}/auth/logout", json={})
        assert logout_without_csrf.status_code == 403, logout_without_csrf.text

        logout = client.post(f"{base}/auth/logout", json={}, headers={"X-CSRF-Token": csrf})
        assert logout.status_code == 200, logout.text
        assert logout.json().get("ok") is True

        me_after_logout = client.get(f"{base}/auth/me")
        assert me_after_logout.status_code == 401, me_after_logout.text
