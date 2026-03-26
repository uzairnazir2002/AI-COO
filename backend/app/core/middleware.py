import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.core.config import Settings, get_settings
from app.core.error_envelope import error_payload
from app.core.slo_metrics import record_runtime_sample


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if self._https_required_but_missing(request, settings):
            return JSONResponse(
                status_code=400,
                content=error_payload(
                    request=request,
                    status_code=400,
                    message="HTTPS is required",
                    details="HTTPS is required",
                ),
            )
        if self._csrf_validation_failed(request, settings):
            return JSONResponse(
                status_code=403,
                content=error_payload(
                    request=request,
                    status_code=403,
                    message="CSRF validation failed",
                    details="CSRF validation failed",
                ),
            )
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        clear_contextvars()
        bind_contextvars(request_id=request_id, path=request.url.path, method=request.method)
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
        record_runtime_sample(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=elapsed,
        )
        clear_contextvars()
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

    @staticmethod
    def _https_required_but_missing(request: Request, settings: Settings) -> bool:
        if not settings.enforce_https:
            return False
        if settings.env == "development":
            return False
        forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
        is_https = request.url.scheme == "https" or forwarded_proto == "https"
        return not is_https
