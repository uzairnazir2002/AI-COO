import hashlib
import secrets
import uuid
from datetime import timedelta, timezone

from fastapi import Request

from app.core.config import get_settings
from app.core.mfa import build_totp_uri, decrypt_mfa_secret, encrypt_mfa_secret, generate_totp_secret, verify_totp_code
from app.core.pii_crypto import pii_decrypt
from app.core.security import access_ttl, create_token, decode_token, hash_password, refresh_ttl, verify_password
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.auth_repo import AuthRepo
from app.domain.repos.org_repo import OrgRepo
from app.domain.repos.outbox_repo import OutboxRepo
from app.domain.schemas.auth import SessionOut, TokenOut
from app.domain.services.errors import ConflictError, UnauthorizedError
from app.utils.time import utc_now


def _h(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _generate_recovery_codes(count: int = 10) -> list[str]:
    return [secrets.token_hex(4).upper() for _ in range(count)]


class AuthService:
    def __init__(self, auth_repo: AuthRepo, org_repo: OrgRepo, audit_repo: AuditRepo, outbox_repo: OutboxRepo | None = None):
        self.auth_repo = auth_repo
        self.org_repo = org_repo
        self.audit_repo = audit_repo
        self.outbox_repo = outbox_repo

    async def _issue_confirmation_token(self, *, user_id: uuid.UUID, email: str, dedupe_suffix: str) -> str:
        raw_token = secrets.token_urlsafe(32)
        token_hash = _h(raw_token)
        await self.auth_repo.create_confirmation_token(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=utc_now() + timedelta(hours=24),
        )
        if self.outbox_repo is not None:
            await self.outbox_repo.create_event(
                org_id=None,
                event_type="email.send",
                payload={
                    "to": email.lower(),
                    "subject": "Confirm your AI COO account",
                    "body": (
                        "Welcome to AI COO.\n\n"
                        "Confirm your account with this token:\n"
                        f"{raw_token}\n\n"
                        "Call POST /api/v1/auth/confirm with {\"token\":\"...\"}."
                    ),
                },
                dedupe_key=f"register-confirm:{user_id}:{dedupe_suffix}",
                max_attempts=5,
            )
        return raw_token

    async def register(self, email: str, password: str):
        existing = await self.auth_repo.get_user_by_email(email.lower())
        if existing:
            raise ConflictError("Email already exists")
        user = await self.auth_repo.create_user(email=email, password_hash=hash_password(password), is_active=False)
        await self._issue_confirmation_token(user_id=user.id, email=email, dedupe_suffix="register")
        await self.audit_repo.log(user.id, None, "auth.register", "user", str(user.id), {"email": email.lower()})
        return user

    async def resend_confirmation(self, email: str) -> tuple[bool, bool]:
        user = await self.auth_repo.get_user_by_email(email.lower())
        if not user:
            return False, False
        if user.is_active:
            return False, True
        await self._issue_confirmation_token(
            user_id=user.id,
            email=email,
            dedupe_suffix=f"resend:{secrets.token_hex(6)}",
        )
        await self.audit_repo.log(user.id, None, "auth.confirm.resend", "user", str(user.id), {"email": email.lower()})
        return True, False

    async def login(
        self,
        email: str,
        password: str,
        request: Request,
        mfa_code: str | None = None,
        mfa_recovery_code: str | None = None,
    ) -> TokenOut:
        user = await self.auth_repo.get_user_by_email(email.lower())
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid credentials")
        await self._verify_mfa(user=user, mfa_code=mfa_code, mfa_recovery_code=mfa_recovery_code)
        if not user.mfa_enabled:
            owner_orgs = await self.org_repo.owner_org_ids_requiring_mfa(user.id)
            if owner_orgs:
                raise UnauthorizedError("MFA is required by organization policy")
        return await self._issue_tokens(user.id, request, audit_action="auth.login")

    async def authenticate_for_reauth(
        self,
        *,
        user_id: uuid.UUID,
        password: str,
        mfa_code: str | None = None,
        mfa_recovery_code: str | None = None,
    ) -> None:
        user = await self.auth_repo.get_user(user_id)
        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid credentials")
        await self._verify_mfa(user=user, mfa_code=mfa_code, mfa_recovery_code=mfa_recovery_code)

    async def _verify_mfa(
        self,
        *,
        user,
        mfa_code: str | None = None,
        mfa_recovery_code: str | None = None,
    ) -> None:
        if not user.mfa_enabled:
            return
        if not user.mfa_secret_encrypted:
            raise UnauthorizedError("MFA is misconfigured")
        if mfa_code:
            if not verify_totp_code(decrypt_mfa_secret(user.mfa_secret_encrypted), mfa_code):
                raise UnauthorizedError("Invalid MFA code")
            return
        if mfa_recovery_code:
            entered = _h(mfa_recovery_code.strip().upper())
            existing = list(user.mfa_recovery_code_hashes or [])
            if entered not in existing:
                raise UnauthorizedError("Invalid recovery code")
            user.mfa_recovery_code_hashes = [code for code in existing if code != entered]
            await self.auth_repo.save_user(user)
            await self.audit_repo.log(
                user.id,
                None,
                "auth.mfa.recovery_code_used",
                "user",
                str(user.id),
                {"remaining": len(user.mfa_recovery_code_hashes)},
            )
            return
        raise UnauthorizedError("MFA code required")

    async def issue_registration_tokens(self, user_id: uuid.UUID, request: Request) -> TokenOut:
        return await self._issue_tokens(user_id, request)

    async def _issue_tokens(self, user_id: uuid.UUID, request: Request, audit_action: str | None = None) -> TokenOut:
        refresh = create_token(str(user_id), "refresh", refresh_ttl())
        access = create_token(str(user_id), "access", access_ttl())
        refresh_payload = decode_token(refresh) or {}
        exp = utc_now().replace(tzinfo=timezone.utc)
        exp = exp.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)
        await self.auth_repo.create_token_session(
            user_id=user_id,
            refresh_token_hash=_h(refresh),
            expires_at=exp,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
        if audit_action:
            await self.audit_repo.log(user_id, None, audit_action, "user", str(user_id), {})
        return TokenOut(access_token=access, refresh_token=refresh, expires_in=int(access_ttl().total_seconds()))

    async def refresh(self, refresh_token: str, request: Request) -> TokenOut:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid refresh token")
        session = await self.auth_repo.get_token_session(_h(refresh_token))
        now = utc_now()
        if not session:
            raise UnauthorizedError("Refresh revoked")
        if session.is_revoked:
            if session.replaced_by_token_hash:
                revoked_count = await self.auth_repo.revoke_all_user_sessions(session.user_id)
                await self.audit_repo.log(
                    session.user_id,
                    None,
                    "auth.refresh.reuse_detected",
                    "token_session",
                    str(session.id),
                    {"revoked_active_sessions": revoked_count},
                )
            raise UnauthorizedError("Refresh revoked")
        if session.expires_at <= now:
            raise UnauthorizedError("Refresh revoked")
        user_id = uuid.UUID(payload["sub"])
        user = await self.auth_repo.get_user(user_id)
        if not user or not user.is_active:
            await self.auth_repo.revoke_token(session)
            raise UnauthorizedError("Account is not active")
        access = create_token(str(user_id), "access", access_ttl())
        new_refresh = create_token(str(user_id), "refresh", refresh_ttl())
        p2 = decode_token(new_refresh) or {}
        await self.auth_repo.rotate_token(session, _h(new_refresh))
        await self.auth_repo.create_token_session(
            user_id=user_id,
            refresh_token_hash=_h(new_refresh),
            expires_at=utc_now().fromtimestamp(p2["exp"], tz=timezone.utc),
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
        await self.audit_repo.log(user_id, None, "auth.refresh", "user", str(user_id), {})
        return TokenOut(access_token=access, refresh_token=new_refresh, expires_in=int(access_ttl().total_seconds()))

    async def logout(self, refresh_token: str, user_id: uuid.UUID | None) -> None:
        session = await self.auth_repo.get_token_session(_h(refresh_token))
        if session:
            await self.auth_repo.revoke_token(session)
        await self.audit_repo.log(user_id, None, "auth.logout", "token_session", str(user_id or "anonymous"), {})

    async def accept_invite(self, token: str, password: str):
        invite = await self.org_repo.get_invite_by_hash(_h(token))
        now = utc_now()
        if not invite or invite.accepted_at is not None or invite.expires_at <= now:
            raise UnauthorizedError("Invalid or expired invite token")
        invite_email = (pii_decrypt(invite.email) or invite.email).lower()
        user = await self.auth_repo.get_user_by_email(invite_email)
        if user:
            user.password_hash = hash_password(password)
            user.is_active = True
            await self.auth_repo.save_user(user)
        else:
            user = await self.auth_repo.create_user(invite_email, hash_password(password), is_active=True)
        membership = await self.org_repo.membership(user.id, invite.org_id)
        if not membership:
            await self.org_repo.add_membership(user.id, invite.org_id, invite.role)
        invite.accepted_at = now
        await self.audit_repo.log(
            user.id,
            invite.org_id,
            "org.invite.accept",
            "organization_invite",
            str(invite.id),
            {"role": invite.role},
        )
        return user

    async def confirm_registration(self, token: str):
        rec = await self.auth_repo.get_confirmation_token(_h(token))
        now = utc_now()
        if not rec or rec.used_at is not None or rec.expires_at <= now:
            raise UnauthorizedError("Invalid or expired confirmation token")
        user = await self.auth_repo.get_user(rec.user_id)
        if not user:
            raise UnauthorizedError("Invalid confirmation token")
        user.is_active = True
        await self.auth_repo.save_user(user)
        await self.auth_repo.mark_confirmation_token_used(rec)
        await self.audit_repo.log(user.id, None, "auth.confirm", "user", str(user.id), {})
        return user

    async def setup_mfa(self, *, user_id: uuid.UUID, password: str) -> tuple[str, str]:
        user = await self.auth_repo.get_user(user_id)
        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid credentials")
        secret = generate_totp_secret()
        user.mfa_secret_encrypted = encrypt_mfa_secret(secret)
        user.mfa_enabled = False
        user.mfa_enabled_at = None
        await self.auth_repo.save_user(user)
        issuer = get_settings().mfa_totp_issuer
        uri = build_totp_uri(email=user.email, secret=secret, issuer=issuer)
        await self.audit_repo.log(user.id, None, "auth.mfa.setup", "user", str(user.id), {})
        return secret, uri

    async def enable_mfa(self, *, user_id: uuid.UUID, code: str) -> list[str]:
        user = await self.auth_repo.get_user(user_id)
        if not user or not user.mfa_secret_encrypted:
            raise UnauthorizedError("MFA setup is required")
        secret = decrypt_mfa_secret(user.mfa_secret_encrypted)
        if not verify_totp_code(secret, code):
            raise UnauthorizedError("Invalid MFA code")
        recovery_codes = _generate_recovery_codes()
        user.mfa_enabled = True
        user.mfa_enabled_at = utc_now()
        user.mfa_recovery_code_hashes = [_h(code) for code in recovery_codes]
        await self.auth_repo.save_user(user)
        await self.audit_repo.log(
            user.id,
            None,
            "auth.mfa.enable",
            "user",
            str(user.id),
            {"recovery_codes_issued": len(recovery_codes)},
        )
        return recovery_codes

    async def disable_mfa(self, *, user_id: uuid.UUID, password: str, code: str) -> None:
        user = await self.auth_repo.get_user(user_id)
        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid credentials")
        if not user.mfa_enabled or not user.mfa_secret_encrypted:
            raise UnauthorizedError("MFA is not enabled")
        secret = decrypt_mfa_secret(user.mfa_secret_encrypted)
        if not verify_totp_code(secret, code):
            raise UnauthorizedError("Invalid MFA code")
        user.mfa_enabled = False
        user.mfa_secret_encrypted = None
        user.mfa_enabled_at = None
        user.mfa_recovery_code_hashes = []
        await self.auth_repo.save_user(user)
        await self.audit_repo.log(user.id, None, "auth.mfa.disable", "user", str(user.id), {})

    async def get_mfa_status(self, *, user_id: uuid.UUID) -> dict:
        user = await self.auth_repo.get_user(user_id)
        if not user:
            raise UnauthorizedError("User not found")
        return {
            "enabled": bool(user.mfa_enabled),
            "configured": bool(user.mfa_secret_encrypted),
            "enabled_at": user.mfa_enabled_at,
            "recovery_codes_remaining": len(user.mfa_recovery_code_hashes or []),
        }

    async def regenerate_recovery_codes(self, *, user_id: uuid.UUID, password: str, code: str) -> list[str]:
        user = await self.auth_repo.get_user(user_id)
        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid credentials")
        if not user.mfa_enabled or not user.mfa_secret_encrypted:
            raise UnauthorizedError("MFA is not enabled")
        secret = decrypt_mfa_secret(user.mfa_secret_encrypted)
        if not verify_totp_code(secret, code):
            raise UnauthorizedError("Invalid MFA code")
        recovery_codes = _generate_recovery_codes()
        user.mfa_recovery_code_hashes = [_h(item) for item in recovery_codes]
        await self.auth_repo.save_user(user)
        await self.audit_repo.log(
            user.id,
            None,
            "auth.mfa.recovery_codes.regenerate",
            "user",
            str(user.id),
            {"count": len(recovery_codes)},
        )
        return recovery_codes

    async def list_sessions(self, *, user_id: uuid.UUID, current_refresh_token: str | None) -> list[SessionOut]:
        current_hash = _h(current_refresh_token) if current_refresh_token else None
        sessions = await self.auth_repo.list_sessions_for_user(user_id=user_id, include_revoked=False)
        result: list[SessionOut] = []
        for session in sessions:
            is_current = bool(current_hash and session.refresh_token_hash == current_hash)
            result.append(
                SessionOut(
                    id=session.id,
                    created_at=session.created_at,
                    expires_at=session.expires_at,
                    last_used_at=session.last_used_at,
                    user_agent=pii_decrypt(session.user_agent),
                    ip_address=pii_decrypt(session.ip_address),
                    is_revoked=session.is_revoked,
                    is_current=is_current,
                )
            )
        return result

    async def revoke_session(self, *, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
        session = await self.auth_repo.get_session_by_id(session_id=session_id, user_id=user_id)
        if not session:
            raise UnauthorizedError("Session not found")
        await self.auth_repo.revoke_session(session)
        await self.audit_repo.log(user_id, None, "auth.session.revoke", "token_session", str(session.id), {})

    async def revoke_other_sessions(self, *, user_id: uuid.UUID, current_refresh_token: str | None) -> int:
        current_session = None
        if current_refresh_token:
            current_session = await self.auth_repo.get_token_session(_h(current_refresh_token))
            if current_session and current_session.user_id != user_id:
                current_session = None
        revoked_count = await self.auth_repo.revoke_all_user_sessions(
            user_id,
            except_session_id=current_session.id if current_session else None,
        )
        await self.audit_repo.log(user_id, None, "auth.session.revoke_others", "user", str(user_id), {"revoked": revoked_count})
        return revoked_count
