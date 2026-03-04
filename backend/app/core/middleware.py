import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import Settings, get_settings


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if self._csrf_validation_failed(request, settings):
            return JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{elapsed:.2f}"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if settings.env != "development":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    def _csrf_validation_failed(self, request: Request, settings: Settings) -> bool:
        if not settings.auth_cookie_mode:
            return False
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return False
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            return False
        # Only enforce for authenticated cookie-mode requests.
        has_auth_cookie = request.cookies.get(settings.access_cookie_name) or request.cookies.get(
            settings.refresh_cookie_name
        )
        if not has_auth_cookie:
            return False
        csrf_cookie = request.cookies.get(settings.csrf_cookie_name)
        csrf_header = request.headers.get(settings.csrf_header_name)
        return not csrf_cookie or not csrf_header or csrf_cookie != csrf_header
