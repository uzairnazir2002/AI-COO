import secrets
import re
import uuid
from datetime import timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.core.auth_lockout import clear_login_failures, is_locked, record_login_failure
from app.core.config import get_settings
from app.core.rate_limit import enforce_auth_rate_limit
from app.core.security import access_ttl, create_token, refresh_ttl
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.models.outbox_event import OutboxEvent
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.auth_repo import AuthRepo
from app.domain.repos.outbox_repo import OutboxRepo
from app.domain.repos.org_repo import OrgRepo
from app.domain.schemas.auth import (
    AccountDeletionRequestIn,
    ConfirmIn,
    DeletionRequestOut,
    DevConfirmationTokenOut,
    InviteAcceptIn,
    LoginIn,
    LogoutIn,
    MeOut,
    MeOrg,
    MeUser,
    MfaDisableIn,
    MfaEnableIn,
    MfaRecoveryCodesOut,
    MfaRecoveryCodesRegenerateIn,
    MfaSetupIn,
    MfaSetupOut,
    MfaStatusOut,
    RegisterIn,
    RegisterOut,
    ResendConfirmationIn,
    ResendConfirmationOut,
    RevokeOthersIn,
    ReauthIn,
    ReauthOut,
    SessionListOut,
    TokenOut,
    TokenRefreshIn,
)
from app.domain.schemas.privacy import DeletionRequestItemOut, DeletionRequestListOut
from app.domain.services.auth_service import AuthService
from app.domain.services.errors import UnauthorizedError
from app.domain.services.privacy_service import PrivacyService
from app.domain.repos.deletion_repo import DeletionRepo

router = APIRouter()
_CONFIRM_TOKEN_RE = re.compile(r"token:\n([A-Za-z0-9_-]+)")


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    if not settings.auth_cookie_mode:
        return
    csrf_token = secrets.token_urlsafe(24)
    response.set_cookie(
        key=settings.access_cookie_name,
        value=access_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=int(access_ttl().total_seconds()),
        path="/",
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=int(refresh_ttl().total_seconds()),
        path="/",
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=int(refresh_ttl().total_seconds()),
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    for name in (settings.access_cookie_name, settings.refresh_cookie_name, settings.csrf_cookie_name):
        response.delete_cookie(name, path="/")


def _token_response(tok: TokenOut) -> TokenOut:
    settings = get_settings()
    if not settings.auth_cookie_mode:
        return tok
    return TokenOut(access_token=None, refresh_token=None, token_type="cookie", expires_in=tok.expires_in)


def _extract_confirmation_token(body: str | None) -> str | None:
    if not body:
        return None
    match = _CONFIRM_TOKEN_RE.search(body)
    if not match:
        return None
    return match.group(1)


def _get_refresh_token_from_request(*, request: Request, body_token: str | None = None) -> str | None:
    settings = get_settings()
    refresh_token = body_token
    if not refresh_token and settings.auth_cookie_mode:
        refresh_token = request.cookies.get(settings.refresh_cookie_name)
    return refresh_token


@router.post("/register", response_model=RegisterOut)
async def register(request: Request, response: Response, body: RegisterIn, db: AsyncSession = Depends(get_db)):
    await enforce_auth_rate_limit(request, "register", 10)
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db), OutboxRepo(db))
    user = await svc.register(body.email, body.password)
    tok = await svc.issue_registration_tokens(user.id, request)
    _set_auth_cookies(response, tok.access_token, tok.refresh_token)
    await db.commit()
    body_token = _token_response(tok)
    return RegisterOut(
        user_id=user.id,
        access_token=body_token.access_token,
        refresh_token=body_token.refresh_token,
        token_type=body_token.token_type,
        expires_in=body_token.expires_in,
        account_confirmed=False,
    )


@router.post("/login", response_model=TokenOut)
async def login(request: Request, response: Response, body: LoginIn, db: AsyncSession = Depends(get_db)):
    await enforce_auth_rate_limit(request, "login", 20)
    email = body.email.strip().lower()
    client_ip = request.client.host if request.client else None
    lock = await is_locked(email, client_ip)
    if lock.locked:
        await AuditRepo(db).log(
            None,
            None,
            "auth.login.locked",
            "user",
            email,
            {
                "email": email,
                "ip_address": client_ip,
                "retry_after_seconds": lock.remaining_seconds,
                "escalation_level": lock.escalation_level,
            },
        )
        await db.commit()
        raise HTTPException(status_code=429, detail="Too many failed login attempts. Try again later.")
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db), OutboxRepo(db))
    try:
        tok = await svc.login(email, body.password, request, body.mfa_code, body.mfa_recovery_code)
    except UnauthorizedError as exc:
        result = await record_login_failure(email, client_ip)
        await AuditRepo(db).log(
            None,
            None,
            "auth.login.failed",
            "user",
            email,
            {
                "email": email,
                "ip_address": client_ip,
                "failure_count": result.failure_count,
                "locked": result.locked,
                "retry_after_seconds": result.remaining_seconds,
                "escalation_level": result.escalation_level,
                "escalated": result.escalated,
            },
        )
        if result.escalated:
            await AuditRepo(db).log(
                None,
                None,
                "auth.login.lockout.escalated",
                "user",
                email,
                {
                    "email": email,
                    "ip_address": client_ip,
                    "failure_count": result.failure_count,
                    "escalation_level": result.escalation_level,
                },
            )
        if result.locked:
            await AuditRepo(db).log(
                None,
                None,
                "auth.login.locked",
                "user",
                email,
                {
                    "email": email,
                    "ip_address": client_ip,
                    "retry_after_seconds": result.remaining_seconds,
                    "escalation_level": result.escalation_level,
                },
            )
        await db.commit()
        if result.locked:
            raise HTTPException(status_code=429, detail="Too many failed login attempts. Try again later.") from exc
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    await clear_login_failures(email, client_ip)
    _set_auth_cookies(response, tok.access_token, tok.refresh_token)
    await db.commit()
    return _token_response(tok)


@router.post("/refresh", response_model=TokenOut)
async def refresh(
    request: Request,
    response: Response,
    body: TokenRefreshIn,
    db: AsyncSession = Depends(get_db),
):
    await enforce_auth_rate_limit(request, "refresh", 30)
    refresh_token = _get_refresh_token_from_request(request=request, body_token=body.refresh_token)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db), OutboxRepo(db))
    tok = await svc.refresh(refresh_token, request)
    _set_auth_cookies(response, tok.access_token, tok.refresh_token)
    await db.commit()
    return _token_response(tok)


@router.post("/invite/accept", response_model=RegisterOut)
async def accept_invite(request: Request, body: InviteAcceptIn, db: AsyncSession = Depends(get_db)):
    await enforce_auth_rate_limit(request, "accept_invite", 10)
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db), OutboxRepo(db))
    user = await svc.accept_invite(body.token, body.password)
    await db.commit()
    return RegisterOut(user_id=user.id, account_confirmed=True)


@router.post("/confirm", response_model=RegisterOut)
async def confirm(request: Request, body: ConfirmIn, db: AsyncSession = Depends(get_db)):
    await enforce_auth_rate_limit(request, "confirm", 10)
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db), OutboxRepo(db))
    if body.password:
        user = await svc.accept_invite(body.token, body.password)
    else:
        user = await svc.confirm_registration(body.token)
    await db.commit()
    return RegisterOut(user_id=user.id, account_confirmed=True)


@router.post("/resend-confirmation", response_model=ResendConfirmationOut)
async def resend_confirmation(request: Request, body: ResendConfirmationIn, db: AsyncSession = Depends(get_db)):
    await enforce_auth_rate_limit(request, "resend_confirmation", 10)
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db), OutboxRepo(db))
    sent, already_active = await svc.resend_confirmation(body.email)
    await db.commit()
    return ResendConfirmationOut(ok=True, sent=sent, already_active=already_active)


@router.get("/dev/confirmation-token", response_model=DevConfirmationTokenOut)
async def dev_confirmation_token(
    email: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    if settings.env != "development":
        raise HTTPException(status_code=404, detail="Not found")

    rows = await db.execute(
        select(OutboxEvent)
        .where(OutboxEvent.event_type == "email.send")
        .order_by(OutboxEvent.created_at.desc())
        .limit(100)
    )
    events = list(rows.scalars().all())
    email_lower = email.strip().lower()
    for event in events:
        payload = event.payload or {}
        to_email = str(payload.get("to", "")).strip().lower()
        if to_email != email_lower:
            continue
        token = _extract_confirmation_token(str(payload.get("body", "")))
        if token:
            return DevConfirmationTokenOut(email=email_lower, token=token, found=True)

    return DevConfirmationTokenOut(email=email_lower, token=None, found=False)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    body: LogoutIn | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    refresh_token = _get_refresh_token_from_request(request=request, body_token=(body.refresh_token if body else None))
    if refresh_token:
        svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db), OutboxRepo(db))
        await svc.logout(refresh_token, user.id)
        await db.commit()
    _clear_auth_cookies(response)
    return {"ok": True}


@router.get("/me", response_model=MeOut)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    orgs = await OrgRepo(db).list_orgs_for_user(user.id)
    return MeOut(
        user=MeUser(id=user.id, email=user.email, created_at=user.created_at),
        orgs=[MeOrg(org_id=o.id, role=str(m.role), name=o.name) for o, m in orgs],
    )


@router.get("/mfa/status", response_model=MfaStatusOut)
async def mfa_status(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db), OutboxRepo(db))
    status = await svc.get_mfa_status(user_id=user.id)
    return MfaStatusOut(**status)


@router.post("/mfa/setup", response_model=MfaSetupOut)
async def mfa_setup(
    request: Request,
    body: MfaSetupIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await enforce_auth_rate_limit(request, "mfa_setup", 15)
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db), OutboxRepo(db))
    secret, uri = await svc.setup_mfa(user_id=user.id, password=body.password)
    await db.commit()
    return MfaSetupOut(secret=secret, otpauth_url=uri)


@router.post("/mfa/enable", response_model=MfaRecoveryCodesOut)
async def mfa_enable(
    request: Request,
    body: MfaEnableIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await enforce_auth_rate_limit(request, "mfa_enable", 20)
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db), OutboxRepo(db))
    recovery_codes = await svc.enable_mfa(user_id=user.id, code=body.code)
    await db.commit()
    return MfaRecoveryCodesOut(recovery_codes=recovery_codes)


@router.post("/mfa/disable")
async def mfa_disable(
    request: Request,
    body: MfaDisableIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await enforce_auth_rate_limit(request, "mfa_disable", 20)
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db), OutboxRepo(db))
    await svc.disable_mfa(user_id=user.id, password=body.password, code=body.code)
    await db.commit()
    return {"ok": True}


@router.post("/mfa/recovery-codes/regenerate", response_model=MfaRecoveryCodesOut)
async def mfa_regenerate_recovery_codes(
    request: Request,
    body: MfaRecoveryCodesRegenerateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await enforce_auth_rate_limit(request, "mfa_recovery_regenerate", 10)
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db), OutboxRepo(db))
    recovery_codes = await svc.regenerate_recovery_codes(
        user_id=user.id,
        password=body.password,
        code=body.code,
    )
    await db.commit()
    return MfaRecoveryCodesOut(recovery_codes=recovery_codes)


@router.get("/sessions", response_model=SessionListOut)
async def list_sessions(
    request: Request,
    refresh_token: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_refresh_token = _get_refresh_token_from_request(request=request, body_token=refresh_token)
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db), OutboxRepo(db))
    sessions = await svc.list_sessions(user_id=user.id, current_refresh_token=current_refresh_token)
    return SessionListOut(items=sessions)


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db), OutboxRepo(db))
    await svc.revoke_session(user_id=user.id, session_id=session_id)
    await db.commit()
    return {"ok": True}


@router.post("/sessions/revoke-others")
async def revoke_other_sessions(
    request: Request,
    body: RevokeOthersIn = Body(default_factory=RevokeOthersIn),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_refresh_token = _get_refresh_token_from_request(request=request, body_token=body.refresh_token)
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db), OutboxRepo(db))
    revoked = await svc.revoke_other_sessions(user_id=user.id, current_refresh_token=current_refresh_token)
    await db.commit()
    return {"ok": True, "revoked": revoked}


@router.post("/reauth", response_model=ReauthOut)
async def reauth(
    request: Request,
    body: ReauthIn,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await enforce_auth_rate_limit(request, "reauth", 20)
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    if ctx.role not in {"OWNER", "EDITOR"}:
        raise HTTPException(status_code=403, detail="Forbidden")
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db), OutboxRepo(db))
    await svc.authenticate_for_reauth(
        user_id=user.id,
        password=body.password,
        mfa_code=body.mfa_code,
        mfa_recovery_code=body.mfa_recovery_code,
    )
    settings_row = await OrgRepo(db).get_settings(org_id)
    ttl_minutes = settings_row.sensitive_action_reauth_minutes if settings_row else 30
    ttl_minutes = max(5, min(1440, int(ttl_minutes)))
    token = create_token(
        str(user.id),
        "reauth",
        timedelta(minutes=ttl_minutes),
        extra={"org_id": str(org_id)},
    )
    await AuditRepo(db).log(
        user.id,
        org_id,
        "auth.reauth",
        "user",
        str(user.id),
        {"org_id": str(org_id), "expires_in_minutes": ttl_minutes},
    )
    await db.commit()
    return ReauthOut(ok=True, token=token, expires_in=ttl_minutes * 60)


@router.post("/delete-account", response_model=DeletionRequestOut)
async def request_account_deletion(
    body: AccountDeletionRequestIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = PrivacyService(db, AuditRepo(db), DeletionRepo(db))
    out = await svc.request_account_deletion(user_id=user.id, reason=body.reason)
    await db.commit()
    return DeletionRequestOut(ok=True, request_id=out["request_id"], delete_after=out["delete_after"])


@router.get("/delete-account/requests", response_model=DeletionRequestListOut)
async def list_account_deletion_requests(
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = PrivacyService(db, AuditRepo(db), DeletionRepo(db))
    rows = await svc.list_account_deletion_requests(user_id=user.id, limit=limit)
    return DeletionRequestListOut(items=[DeletionRequestItemOut.model_validate(row) for row in rows])
