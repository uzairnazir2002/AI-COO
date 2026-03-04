import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context, require_roles
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.report_repo import ReportRepo
from app.domain.schemas.reports import ReportItem, ReportsOut
from app.domain.services.report_service import ReportService

router = APIRouter()


@router.get("", response_model=ReportsOut)
async def list_reports(org_id: uuid.UUID = Query(...), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await get_org_context(org_id=org_id, user=user, db=db)
    rows = await ReportService(ReportRepo(db)).list_reports(org_id)
    return ReportsOut(items=[ReportItem(id=r.id, week_start=r.week_start, week_end=r.week_end, created_at=r.created_at) for r in rows])


@router.post("/generate")
async def generate(
    org_id: uuid.UUID = Query(...),
    week_start: date = Query(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER", "EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    report = await ReportService(ReportRepo(db)).generate(org_id, week_start, user.id)
    await AuditRepo(db).log(user.id, org_id, "report.generate", "report", str(report.id), {"week_start": week_start.isoformat()})
    await db.commit()
    return {"report_id": str(report.id)}


@router.get("/{report_id}/download")
async def download(
    report_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    repo = ReportRepo(db)
    report = await repo.get(report_id, org_id)
    if not report:
        return {"url": None}
    url = await ReportService(repo).download_url(report)
    return {"url": url}
