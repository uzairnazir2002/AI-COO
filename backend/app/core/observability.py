from __future__ import annotations

import structlog

from app.core.config import Settings

logger = structlog.get_logger(__name__)


def init_sentry(settings: Settings, service_name: str) -> None:
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk
    except Exception:
        logger.warning("sentry_sdk_not_installed", service=service_name)
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.env,
        traces_sample_rate=settings.sentry_traces_sample_rate,
    )
    logger.info("sentry_initialized", service=service_name, env=settings.env)
