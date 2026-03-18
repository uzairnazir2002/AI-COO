import csv
import io
import json
import uuid
from datetime import date

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context, require_roles
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.import_repo import ImportRepo
from app.domain.repos.import_profile_repo import ImportProfileRepo
from app.domain.repos.plan_repo import PlanRepo
from app.domain.repos.transaction_repo import TransactionRepo
from app.domain.schemas.common import TransactionOut
from app.domain.schemas.transaction import (
    BulkCategoryRemapIn,
    CSVImportOut,
    ImportMappingProfileIn,
    ImportMappingProfileOut,
    ImportMappingProfileUpdateIn,
    ImportHistoryItem,
    ImportHistoryPageOut,
    TransactionCreateIn,
    TransactionPageOut,
    TransactionUpdateIn,
)
from app.domain.services.import_profile_service import ImportProfileService
from app.domain.services.read_cache_service import (
    analytics_summary_cache_prefix,
    cache_delete_prefix,
    cache_get_json,
    cache_set_json,
    transactions_cache_key,
    transactions_cache_prefix,
)
from app.domain.services.errors import ForbiddenError, NotFoundError
from app.domain.services.transaction_service import TransactionService
from app.domain.services.usage_service import UsageService
from app.core.config import get_settings

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
    svc = TransactionService(
        TransactionRepo(db),
        AuditRepo(db),
        usage_service=UsageService(PlanRepo(db)),
        import_repo=ImportRepo(db),
    )
    tx = await svc.create(user.id, body)
    await db.commit()
    await cache_delete_prefix(transactions_cache_prefix(body.org_id))
    await cache_delete_prefix(analytics_summary_cache_prefix(body.org_id))
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
    parsed_from = date.fromisoformat(from_date) if from_date else None
    parsed_to = date.fromisoformat(to_date) if to_date else None
    settings = get_settings()
    cache_key = transactions_cache_key(
        org_id=org_id,
        from_date=parsed_from,
        to_date=parsed_to,
        tx_type=type,
        category=category,
        q=q,
        page=page,
        page_size=page_size,
    )
    cached = await cache_get_json(cache_key)
    if isinstance(cached, dict):
        return TransactionPageOut.model_validate(cached)
    svc = TransactionService(TransactionRepo(db), AuditRepo(db), usage_service=UsageService(PlanRepo(db)), import_repo=ImportRepo(db))
    items, total = await svc.list(
        org_id,
        parsed_from,
        parsed_to,
        type,
        category,
        q,
        page,
        page_size,
    )
    result = TransactionPageOut(
        items=[TransactionOut.model_validate(i) for i in items],
        page=page,
        page_size=page_size,
        total=total,
    )
    await cache_set_json(cache_key, result.model_dump(mode="json"), settings.transactions_cache_ttl_seconds)
    return result


@router.put("/{tx_id}", response_model=dict)
async def update_tx(
    tx_id: uuid.UUID,
    body: TransactionUpdateIn,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER", "EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    svc = TransactionService(TransactionRepo(db), AuditRepo(db), usage_service=UsageService(PlanRepo(db)), import_repo=ImportRepo(db))
    tx = await svc.update(user.id, org_id, tx_id, body)
    await db.commit()
    await cache_delete_prefix(transactions_cache_prefix(org_id))
    await cache_delete_prefix(analytics_summary_cache_prefix(org_id))
    return {"transaction": TransactionOut.model_validate(tx)}


@router.delete("/{tx_id}")
async def delete_tx(
    tx_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER", "EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    svc = TransactionService(TransactionRepo(db), AuditRepo(db), usage_service=UsageService(PlanRepo(db)), import_repo=ImportRepo(db))
    await svc.delete(user.id, org_id, tx_id)
    await db.commit()
    await cache_delete_prefix(transactions_cache_prefix(org_id))
    await cache_delete_prefix(analytics_summary_cache_prefix(org_id))
    return {"ok": True}


@router.post("/import/csv", response_model=CSVImportOut)
async def import_csv(
    org_id: uuid.UUID = Form(...),
    mapping: str | None = Form(None),
    profile_id: uuid.UUID | None = Form(None),
    commit: bool = Form(True),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    parsed_mapping: dict[str, str] | None = None
    if mapping:
        try:
            parsed_mapping = json.loads(mapping)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="Invalid mapping JSON") from exc

    mapping_service = ImportProfileService(ImportProfileRepo(db))
    try:
        resolved_mapping, resolved_profile_id = await mapping_service.resolve_import_mapping(
            org_id=org_id,
            actor_user_id=user.id,
            mapping=parsed_mapping,
            profile_id=profile_id,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    content = await file.read()
    svc = TransactionService(
        TransactionRepo(db),
        AuditRepo(db),
        usage_service=UsageService(PlanRepo(db)),
        import_repo=ImportRepo(db),
    )
    try:
        if commit:
            import_id, preview, inserted = await svc.import_csv(
                user.id,
                org_id,
                content,
                resolved_mapping,
                file.filename or "import.csv",
                mapping_profile_id=resolved_profile_id,
            )
        else:
            import_id, preview = await svc.preview_csv(
                user.id,
                org_id,
                content,
                resolved_mapping,
                file.filename or "preview.csv",
                mapping_profile_id=resolved_profile_id,
            )
            inserted = 0
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if commit:
        await db.commit()
        await cache_delete_prefix(transactions_cache_prefix(org_id))
        await cache_delete_prefix(analytics_summary_cache_prefix(org_id))
    else:
        await db.commit()
    return CSVImportOut(import_id=import_id, preview=preview, inserted_count=inserted, mapping_profile_id=resolved_profile_id)


@router.get("/imports", response_model=ImportHistoryPageOut)
async def list_imports(
    org_id: uuid.UUID = Query(...),
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    rows, total = await ImportRepo(db).list_imports(org_id, page, page_size)
    return ImportHistoryPageOut(
        items=[
            ImportHistoryItem(
                id=row.id,
                file_name=row.file_name,
                status=row.status,
                total_rows=row.total_rows,
                inserted_count=row.inserted_count,
                duplicate_count=row.duplicate_count,
                error_count=row.error_count,
                mapping_profile_id=row.mapping_profile_id,
                created_at=row.created_at,
                created_by=row.created_by,
            )
            for row in rows
        ],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/imports/{import_id}/errors")
async def download_import_errors(
    import_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    record = await ImportRepo(db).get(import_id, org_id)
    if not record:
        raise HTTPException(status_code=404, detail="Import not found")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["row", "reason", "data"])
    writer.writeheader()
    for err in (record.error_rows_json or []):
        writer.writerow(
            {
                "row": err.get("row"),
                "reason": err.get("reason"),
                "data": json.dumps(err.get("data", {})),
            }
        )
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="import-errors-{import_id}.csv"'},
    )


@router.post("/bulk/remap-category")
async def bulk_remap_category(
    body: BulkCategoryRemapIn,
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER", "EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=body.org_id, user=user, db=db)
    svc = TransactionService(TransactionRepo(db), AuditRepo(db), usage_service=UsageService(PlanRepo(db)), import_repo=ImportRepo(db))
    updated_count = await svc.bulk_remap_category(
        user_id=user.id,
        org_id=body.org_id,
        from_category=body.from_category,
        to_category=body.to_category,
        from_date=body.from_date,
        to_date=body.to_date,
    )
    await db.commit()
    await cache_delete_prefix(transactions_cache_prefix(body.org_id))
    await cache_delete_prefix(analytics_summary_cache_prefix(body.org_id))
    return {"ok": True, "updated_count": updated_count}


@router.get("/import-profiles", response_model=list[ImportMappingProfileOut])
async def list_import_profiles(
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    svc = ImportProfileService(ImportProfileRepo(db))
    rows = await svc.list_profiles(org_id=org_id, user_id=user.id)
    return [
        ImportMappingProfileOut(
            id=row.id,
            org_id=row.org_id,
            user_id=row.user_id,
            name=row.name,
            column_map=row.column_map,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.post("/import-profiles", response_model=ImportMappingProfileOut)
async def create_import_profile(
    body: ImportMappingProfileIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = ImportProfileService(ImportProfileRepo(db))
    row = await svc.create_profile(
        org_id=body.org_id,
        actor_user_id=user.id,
        name=body.name,
        column_map=body.column_map,
        shared=body.shared,
    )
    await AuditRepo(db).log(user.id, body.org_id, "transaction.import_profile.create", "import_profile", str(row.id), {"name": row.name})
    await db.commit()
    return ImportMappingProfileOut(
        id=row.id,
        org_id=row.org_id,
        user_id=row.user_id,
        name=row.name,
        column_map=row.column_map,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.put("/import-profiles/{profile_id}", response_model=ImportMappingProfileOut)
async def update_import_profile(
    profile_id: uuid.UUID,
    body: ImportMappingProfileUpdateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = ImportProfileService(ImportProfileRepo(db))
    row = await svc.update_profile(
        profile_id=profile_id,
        org_id=body.org_id,
        actor_user_id=user.id,
        name=body.name,
        column_map=body.column_map,
        shared=body.shared,
    )
    await AuditRepo(db).log(user.id, body.org_id, "transaction.import_profile.update", "import_profile", str(row.id), {"name": row.name})
    await db.commit()
    return ImportMappingProfileOut(
        id=row.id,
        org_id=row.org_id,
        user_id=row.user_id,
        name=row.name,
        column_map=row.column_map,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.delete("/import-profiles/{profile_id}")
async def delete_import_profile(
    profile_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = ImportProfileService(ImportProfileRepo(db))
    await svc.delete_profile(profile_id=profile_id, org_id=org_id, actor_user_id=user.id)
    await AuditRepo(db).log(user.id, org_id, "transaction.import_profile.delete", "import_profile", str(profile_id), {})
    await db.commit()
    return {"ok": True}
