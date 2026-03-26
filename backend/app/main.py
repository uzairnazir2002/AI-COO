from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.error_envelope import detail_to_message, error_payload
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.observability import init_sentry
from app.domain.services.errors import AppError

settings = get_settings()
configure_logging()
init_sentry(settings, service_name="backend-api")

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(RequestContextMiddleware)
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if not origins:
    # Safe local fallback in case env var is present but empty.
    origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Alert-Recalc-Task-Id",
        "X-Alert-Recalc-Status",
        "X-Alert-Recalc-Queued",
    ],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(
            request=request,
            status_code=exc.status_code,
            message=str(exc),
            details=str(exc),
        ),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(
            request=request,
            status_code=exc.status_code,
            message=detail_to_message(exc.detail, "Request failed"),
            details=exc.detail,
        ),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = exc.errors()
    return JSONResponse(
        status_code=422,
        content=error_payload(
            request=request,
            status_code=422,
            message="Validation failed",
            details=details,
        ),
    )


app.include_router(api_router)
