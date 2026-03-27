import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.core.config import get_settings
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.bank_repo import BankRepo
from app.domain.repos.job_repo import JobRepo
from app.domain.repos.payment_repo import PaymentRepo
from app.domain.repos.transaction_repo import TransactionRepo
from app.domain.schemas.integrations import (
    BankAccountOut,
    BankConnectionOut,
    BankSyncEnqueueOut,
    PaymentConnectionOut,
    PaymentReconciliationOut,
    PlaidExchangeIn,
    PlaidExchangeOut,
    PlaidLinkTokenIn,
    PlaidLinkTokenOut,
    StripeConnectIn,
    StripeConnectOut,
)
from app.domain.services.bank_integration_service import BankIntegrationService
from app.domain.services.bank_provider import verify_plaid_webhook_signature
from app.domain.services.payment_integration_service import PaymentIntegrationService
from app.jobs.tasks.banks import sync_bank_connection

router = APIRouter()


def _assert_mutation_role(role: str) -> None:
    if role not in {"OWNER", "EDITOR"}:
        raise HTTPException(status_code=403, detail="Forbidden")


def _to_connection_out(connection, accounts) -> BankConnectionOut:
    return BankConnectionOut(
        id=connection.id,
        org_id=connection.org_id,
        provider=connection.provider,
        status=connection.status,
        institution_id=connection.institution_id,
        institution_name=connection.institution_name,
        connected_by_user_id=connection.connected_by_user_id,
        created_at=connection.created_at,
        updated_at=connection.updated_at,
        revoked_at=connection.revoked_at,
        accounts=[
            BankAccountOut(
                id=row.id,
                external_account_id=row.external_account_id,
                name=row.name,
                mask=row.mask,
                account_type=row.account_type,
                account_subtype=row.account_subtype,
                currency_code=row.currency_code,
                is_active=row.is_active,
            )
            for row in accounts
        ],
    )


def _to_payment_connection_out(connection) -> PaymentConnectionOut:
    return PaymentConnectionOut(
        id=connection.id,
        org_id=connection.org_id,
        provider=connection.provider,
        status=connection.status,
        provider_account_id=connection.provider_account_id,
        connected_by_user_id=connection.connected_by_user_id,
        created_at=connection.created_at,
        updated_at=connection.updated_at,
        metadata_json=connection.metadata_json or {},
    )


@router.post("/banks/plaid/link-token", response_model=PlaidLinkTokenOut)
async def create_plaid_link_token(
    body: PlaidLinkTokenIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    service = BankIntegrationService(BankRepo(db), AuditRepo(db), TransactionRepo(db))
    out = await service.create_link_token(org_id=body.org_id, actor_user_id=user.id)
    await db.commit()
    return PlaidLinkTokenOut(**out)


@router.post("/banks/plaid/exchange", response_model=PlaidExchangeOut)
async def exchange_plaid_public_token(
    body: PlaidExchangeIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    service = BankIntegrationService(BankRepo(db), AuditRepo(db), TransactionRepo(db))
    connection, accounts = await service.exchange_public_token(
        org_id=body.org_id,
        actor_user_id=user.id,
        public_token=body.public_token,
        institution_name_override=body.institution_name,
    )
    await db.commit()
    return PlaidExchangeOut(connection=_to_connection_out(connection, accounts))


@router.get("/banks/connections", response_model=list[BankConnectionOut])
async def list_bank_connections(
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    service = BankIntegrationService(BankRepo(db), AuditRepo(db), TransactionRepo(db))
    connections = await service.list_connections(org_id)
    out = []
    for connection in connections:
        accounts = await service.list_accounts(org_id, connection.id)
        out.append(_to_connection_out(connection, accounts))
    return out


@router.delete("/banks/{connection_id}")
async def revoke_bank_connection(
    connection_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    service = BankIntegrationService(BankRepo(db), AuditRepo(db), TransactionRepo(db))
    await service.revoke_connection(org_id=org_id, actor_user_id=user.id, connection_id=connection_id)
    await db.commit()
    return {"ok": True}


@router.post("/banks/{connection_id}/sync", response_model=BankSyncEnqueueOut)
async def enqueue_bank_sync(
    request: Request,
    connection_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    bank_repo = BankRepo(db)
    connection = await bank_repo.get_connection(connection_id, org_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Bank connection not found")

    dedupe_key = f"bank-sync:{org_id}:{connection_id}"
    job_repo = JobRepo(db)
    existing_job = await job_repo.by_dedupe_key(dedupe_key, org_id)
    if existing_job and existing_job.status in {"PENDING", "RUNNING", "RETRYING"}:
        return BankSyncEnqueueOut(job_id=existing_job.task_id, status=existing_job.status, connection_id=connection_id)

    task = sync_bank_connection.apply_async(
        args=[str(org_id), str(connection_id), str(user.id), str(user.id)],
    )
    task_id = str(task.id)
    await job_repo.upsert_pending(
        task_id=task_id,
        task_name="sync_bank_connection",
        dedupe_key=dedupe_key,
        payload={"org_id": str(org_id), "connection_id": str(connection_id), "triggered_by_user_id": str(user.id)},
        org_id=org_id,
        request_id=getattr(request.state, "request_id", None),
        correlation_id=str(user.id),
    )
    await AuditRepo(db).log(
        user.id,
        org_id,
        "bank.plaid.sync.enqueue",
        "bank_connection",
        str(connection_id),
        {"job_id": task_id},
    )
    await db.commit()
    return BankSyncEnqueueOut(job_id=task_id, status="PENDING", connection_id=connection_id)


@router.post("/banks/plaid/webhook")
async def plaid_webhook(
    request: Request,
    plaid_signature: str | None = Header(default=None, alias="X-Plaid-Signature"),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    payload = await request.body()
    if not verify_plaid_webhook_signature(payload, plaid_signature, settings.plaid_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid Plaid webhook signature")
    body = await request.json()
    item_id = body.get("item_id")
    webhook_type = str(body.get("webhook_type") or "")
    webhook_code = str(body.get("webhook_code") or "")
    if not item_id:
        return {"ok": True}

    # Trigger sync only when Plaid notifies transaction deltas are available.
    should_sync = webhook_type.upper() == "TRANSACTIONS" and webhook_code.upper() in {"SYNC_UPDATES_AVAILABLE", "INITIAL_UPDATE"}
    if not should_sync:
        return {"ok": True}

    bank_repo = BankRepo(db)
    audit_repo = AuditRepo(db)
    job_repo = JobRepo(db)
    connections = await bank_repo.list_active_connections_by_external_item(provider="PLAID", external_item_id=item_id)
    enqueued = 0
    for connection in connections:
        if not connection.connected_by_user_id:
            continue
        dedupe_key = f"bank-sync:{connection.org_id}:{connection.id}"
        existing_job = await job_repo.by_dedupe_key(dedupe_key, connection.org_id)
        if existing_job and existing_job.status in {"PENDING", "RUNNING", "RETRYING"}:
            continue
        task = sync_bank_connection.apply_async(
            args=[str(connection.org_id), str(connection.id), str(connection.connected_by_user_id), "plaid-webhook"],
        )
        task_id = str(task.id)
        await job_repo.upsert_pending(
            task_id=task_id,
            task_name="sync_bank_connection",
            dedupe_key=dedupe_key,
            payload={
                "org_id": str(connection.org_id),
                "connection_id": str(connection.id),
                "triggered_by_user_id": str(connection.connected_by_user_id),
                "source": "plaid-webhook",
            },
            org_id=connection.org_id,
            request_id=getattr(request.state, "request_id", None),
            correlation_id="plaid-webhook",
        )
        await audit_repo.log(
            actor_user_id=None,
            org_id=connection.org_id,
            action="bank.plaid.sync.enqueue.webhook",
            entity_type="bank_connection",
            entity_id=str(connection.id),
            metadata_json={"job_id": task_id, "item_id": item_id, "webhook_code": webhook_code},
        )
        enqueued += 1
    await db.commit()
    return {"ok": True, "enqueued": enqueued}


@router.post("/payments/stripe/connect", response_model=StripeConnectOut)
async def connect_stripe(
    body: StripeConnectIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    service = PaymentIntegrationService(PaymentRepo(db), AuditRepo(db), settings=get_settings())
    connection = await service.connect_stripe(
        org_id=body.org_id,
        actor_user_id=user.id,
        provider_account_id=body.provider_account_id,
        account_label=body.account_label,
    )
    await db.commit()
    return StripeConnectOut(connection=_to_payment_connection_out(connection))


@router.get("/payments/connections", response_model=list[PaymentConnectionOut])
async def list_payment_connections(
    org_id: uuid.UUID = Query(...),
    provider: str = Query(default="STRIPE"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    service = PaymentIntegrationService(PaymentRepo(db), AuditRepo(db), settings=get_settings())
    rows = await service.list_connections(org_id=org_id, provider=provider.upper())
    return [_to_payment_connection_out(row) for row in rows]


@router.post("/payments/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()
    service = PaymentIntegrationService(PaymentRepo(db), AuditRepo(db), settings=get_settings())
    try:
        result = await service.ingest_stripe_webhook(
            payload=payload,
            signature_header=stripe_signature,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return {
        "ok": True,
        "status": result.status,
        "event_id": result.event_id,
        "org_id": str(result.org_id) if result.org_id else None,
    }


@router.get("/payments/reconciliation", response_model=PaymentReconciliationOut)
async def get_payment_reconciliation(
    org_id: uuid.UUID = Query(...),
    provider: str = Query(default="STRIPE"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    to_day = date_to or date.today()
    from_day = date_from or (to_day - timedelta(days=29))
    if from_day > to_day:
        raise HTTPException(status_code=400, detail="date_from must be <= date_to")
    service = PaymentIntegrationService(PaymentRepo(db), AuditRepo(db), settings=get_settings())
    out = await service.reconcile(
        org_id=org_id,
        provider=provider,
        date_from=from_day,
        date_to=to_day,
    )
    return PaymentReconciliationOut(
        org_id=out["org_id"],
        provider=out["provider"],
        date_from=out["date_from"],
        date_to=out["date_to"],
        processor=out["processor"],
        transactions=out["transactions"],
        delta=out["delta"],
    )
