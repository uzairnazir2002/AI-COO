import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import enforce_auth_rate_limit
from app.core.security import access_ttl, refresh_ttl
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.auth_repo import AuthRepo
from app.domain.repos.org_repo import OrgRepo
from app.domain.schemas.auth import (
    InviteAcceptIn,
    LoginIn,
    LogoutIn,
    MeOut,
    MeOrg,
    MeUser,
    RegisterIn,
    RegisterOut,
    TokenOut,
    TokenRefreshIn,
)
from app.domain.services.auth_service import AuthService

router = APIRouter()


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


@router.post("/register", response_model=RegisterOut)
async def register(request: Request, body: RegisterIn, db: AsyncSession = Depends(get_db)):
    await enforce_auth_rate_limit(request, "register", 10)
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db))
    user = await svc.register(body.email, body.password)
    await db.commit()
    return RegisterOut(user_id=user.id)


@router.post("/login", response_model=TokenOut)
async def login(request: Request, response: Response, body: LoginIn, db: AsyncSession = Depends(get_db)):
    await enforce_auth_rate_limit(request, "login", 20)
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db))
    tok = await svc.login(body.email, body.password, request)
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
    settings = get_settings()
    refresh_token = body.refresh_token
    if not refresh_token and settings.auth_cookie_mode:
        refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db))
    tok = await svc.refresh(refresh_token, request)
    _set_auth_cookies(response, tok.access_token, tok.refresh_token)
    await db.commit()
    return _token_response(tok)


@router.post("/invite/accept", response_model=RegisterOut)
async def accept_invite(request: Request, body: InviteAcceptIn, db: AsyncSession = Depends(get_db)):
    await enforce_auth_rate_limit(request, "accept_invite", 10)
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db))
    user = await svc.accept_invite(body.token, body.password)
    await db.commit()
    return RegisterOut(user_id=user.id)


@router.post("/confirm", response_model=RegisterOut)
async def confirm(request: Request, body: InviteAcceptIn, db: AsyncSession = Depends(get_db)):
    # MVP: confirmation is invite token redemption.
    await enforce_auth_rate_limit(request, "confirm", 10)
    svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db))
    user = await svc.accept_invite(body.token, body.password)
    await db.commit()
    return RegisterOut(user_id=user.id)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    body: LogoutIn | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    refresh_token = body.refresh_token if body else None
    if not refresh_token and settings.auth_cookie_mode:
        refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if refresh_token:
        svc = AuthService(AuthRepo(db), OrgRepo(db), AuditRepo(db))
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
