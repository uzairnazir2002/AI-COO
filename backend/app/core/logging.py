import logging
import sys

import structlog


def configure_logging() -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        timestamper,
    ]
    structlog.configure(
        processors=shared + [structlog.processors.JSONRenderer()],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(stream=sys.stdout, format="%(message)s", level=logging.INFO)
