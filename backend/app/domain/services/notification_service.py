import uuid

from app.domain.repos.notification_repo import NotificationRepo


class NotificationService:
    def __init__(self, repo: NotificationRepo):
        self.repo = repo

    async def create_org_notification(
        self,
        *,
        org_id: uuid.UUID,
        category: str,
        title: str,
        message: str | None = None,
        link: str | None = None,
        metadata_json: dict | None = None,
    ) -> None:
        await self.repo.create(
            org_id=org_id,
            user_id=None,
            category=category,
            title=title,
            message=message,
            link=link,
            metadata_json=metadata_json or {},
        )
