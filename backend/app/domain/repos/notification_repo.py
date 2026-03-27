import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.notification import Notification


class NotificationRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        title: str,
        message: str | None,
        category: str = "INFO",
        org_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        link: str | None = None,
        metadata_json: dict | None = None,
    ) -> Notification:
        row = Notification(
            title=title,
            message=message,
            category=category,
            org_id=org_id,
            user_id=user_id,
            link=link,
            metadata_json=metadata_json or {},
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def list_for_user(
        self,
        *,
        user_id: uuid.UUID,
        org_id: uuid.UUID | None,
        unread_only: bool,
        page: int,
        page_size: int,
    ) -> tuple[list[Notification], int]:
        stmt = select(Notification).where(
            or_(
                Notification.user_id == user_id,
                Notification.user_id.is_(None),
            )
        )
        count_stmt = select(func.count()).select_from(Notification).where(
            or_(
                Notification.user_id == user_id,
                Notification.user_id.is_(None),
            )
        )
        if org_id is not None:
            stmt = stmt.where(or_(Notification.org_id == org_id, Notification.org_id.is_(None)))
            count_stmt = count_stmt.where(or_(Notification.org_id == org_id, Notification.org_id.is_(None)))
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
            count_stmt = count_stmt.where(Notification.is_read.is_(False))
        stmt = stmt.order_by(Notification.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = int((await self.db.execute(count_stmt)).scalar_one())
        return items, total

    async def mark_read(self, notification_id: uuid.UUID, *, user_id: uuid.UUID) -> Notification | None:
        row = await self.db.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                or_(Notification.user_id == user_id, Notification.user_id.is_(None)),
            )
        )
        if not row:
            return None
        row.is_read = True
        await self.db.flush()
        return row

    async def mark_all_read(self, *, user_id: uuid.UUID, org_id: uuid.UUID | None) -> int:
        rows, _ = await self.list_for_user(user_id=user_id, org_id=org_id, unread_only=True, page=1, page_size=500)
        for row in rows:
            row.is_read = True
        await self.db.flush()
        return len(rows)
