import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.notification_repo import NotificationRepo
from app.domain.schemas.notification import NotificationOut, NotificationPageOut

router = APIRouter()


@router.get("", response_model=NotificationPageOut)
async def list_notifications(
    org_id: uuid.UUID = Query(...),
    unread_only: bool = False,
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    repo = NotificationRepo(db)
    items, total = await repo.list_for_user(
        user_id=user.id,
        org_id=ctx.org_id,
        unread_only=unread_only,
        page=page,
        page_size=page_size,
    )
    unread_items, unread_total = await repo.list_for_user(
        user_id=user.id,
        org_id=ctx.org_id,
        unread_only=True,
        page=1,
        page_size=1,
    )
    return NotificationPageOut(
        items=[NotificationOut.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
        unread_count=unread_total,
    )


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    repo = NotificationRepo(db)
    item = await repo.mark_read(notification_id, user_id=user.id)
    await db.commit()
    return {"ok": bool(item)}


@router.post("/read-all")
async def mark_all_read(
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    repo = NotificationRepo(db)
    updated = await repo.mark_all_read(user_id=user.id, org_id=ctx.org_id)
    await db.commit()
    return {"ok": True, "updated": updated}
