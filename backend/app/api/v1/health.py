from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.infra.cache import redis_client

router = APIRouter()


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    db_ok = True
    redis_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    try:
        await redis_client.ping()
    except Exception:
        redis_ok = False
    return {"ok": db_ok and redis_ok, "db": db_ok, "redis": redis_ok}
