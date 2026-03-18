import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()


def _pool_setting(default: int, role_override: int | None) -> int:
    return role_override if role_override is not None else default


app_role = os.getenv("APP_ROLE", "api").strip().lower()
is_worker_role = app_role in {"worker", "beat"}
pool_size = _pool_setting(settings.db_pool_size, settings.worker_db_pool_size if is_worker_role else settings.api_db_pool_size)
max_overflow = _pool_setting(
    settings.db_max_overflow,
    settings.worker_db_max_overflow if is_worker_role else settings.api_db_max_overflow,
)
pool_timeout = _pool_setting(
    settings.db_pool_timeout_seconds,
    settings.worker_db_pool_timeout_seconds if is_worker_role else settings.api_db_pool_timeout_seconds,
)
pool_recycle = _pool_setting(
    settings.db_pool_recycle_seconds,
    settings.worker_db_pool_recycle_seconds if is_worker_role else settings.api_db_pool_recycle_seconds,
)

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_timeout=pool_timeout,
    pool_recycle=pool_recycle,
    pool_use_lifo=True,
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
