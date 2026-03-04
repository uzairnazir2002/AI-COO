import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context, require_roles
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.transaction_repo import TransactionRepo
from app.domain.schemas.common import TransactionOut
from app.domain.schemas.transaction import (
    BulkCategoryRemapIn,
    CSVImportOut,
    TransactionCreateIn,
    TransactionPageOut,
    TransactionUpdateIn,
)
from app.domain.services.transaction_service import TransactionService

router = APIRouter()


def _assert_mutation_role(role: str) -> None:
    if role not in {"OWNER", "EDITOR"}:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("", response_model=dict)
async def create_tx(
    body: TransactionCreateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = TransactionService(TransactionRepo(db), AuditRepo(db))
    tx = await svc.create(user.id, body)
    await db.commit()
    return {"transaction": TransactionOut.model_validate(tx)}


@router.get("", response_model=TransactionPageOut)
async def list_tx(
    org_id: uuid.UUID = Query(...),
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
    type: str | None = None,
    category: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    svc = TransactionService(TransactionRepo(db), AuditRepo(db))
    from datetime import date

    items, total = await svc.list(
        org_id,
        date.fromisoformat(from_date) if from_date else None,
        date.fromisoformat(to_date) if to_date else None,
        type,
        category,
        q,
        page,
        page_size,
    )
    return TransactionPageOut(
        items=[TransactionOut.model_validate(i) for i in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.put("/{tx_id}", response_model=dict)
async def update_tx(
    tx_id: uuid.UUID,
    body: TransactionUpdateIn,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER", "EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    svc = TransactionService(TransactionRepo(db), AuditRepo(db))
    tx = await svc.update(user.id, org_id, tx_id, body)
    await db.commit()
    return {"transaction": TransactionOut.model_validate(tx)}


@router.delete("/{tx_id}")
async def delete_tx(
    tx_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER", "EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    svc = TransactionService(TransactionRepo(db), AuditRepo(db))
    await svc.delete(user.id, org_id, tx_id)
    await db.commit()
    return {"ok": True}


@router.post("/import/csv", response_model=CSVImportOut)
async def import_csv(
    org_id: uuid.UUID = Form(...),
    mapping: str = Form(...),
    commit: bool = Form(True),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        parsed_mapping = json.loads(mapping)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="Invalid mapping JSON") from exc

    content = await file.read()
    svc = TransactionService(TransactionRepo(db), AuditRepo(db))
    try:
        if commit:
            import_id, preview, inserted = await svc.import_csv(user.id, org_id, content, parsed_mapping)
        else:
            import_id, preview = await svc.preview_csv(org_id, content, parsed_mapping)
            inserted = 0
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if commit:
        await db.commit()
    return CSVImportOut(import_id=import_id, preview=preview, inserted_count=inserted)


@router.post("/bulk/remap-category")
async def bulk_remap_category(
    body: BulkCategoryRemapIn,
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER", "EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=body.org_id, user=user, db=db)
    svc = TransactionService(TransactionRepo(db), AuditRepo(db))
    updated_count = await svc.bulk_remap_category(
        user_id=user.id,
        org_id=body.org_id,
        from_category=body.from_category,
        to_category=body.to_category,
        from_date=body.from_date,
        to_date=body.to_date,
    )
    await db.commit()
    return {"ok": True, "updated_count": updated_count}
