import asyncio
import json
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.alerts_repo import AlertRepo
from app.domain.repos.analytics_repo import AnalyticsRepo
from app.domain.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/stream")
async def stream_updates(
    org_id: uuid.UUID = Query(...),
    interval_seconds: int = Query(default=10, ge=3, le=60),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)

    async def event_gen():
        while True:
            today = date.today()
            from_date = today.replace(day=1)
            summary = await AnalyticsService(AnalyticsRepo(db)).summary(org_id, from_date, today)
            open_alerts = await AlertRepo(db).list_alerts(org_id, "OPEN")
            payload = {
                "org_id": str(org_id),
                "summary": {k: str(v) for k, v in summary.items()},
                "open_alerts": len(open_alerts),
                "ts": today.isoformat(),
            }
            yield f"event: update\ndata: {json.dumps(payload)}\n\n"
            await asyncio.sleep(interval_seconds)

    return StreamingResponse(event_gen(), media_type="text/event-stream")
