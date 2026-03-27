import base64
import hashlib
import hmac
import secrets
import struct
from datetime import datetime, timezone
from urllib.parse import quote

from app.core.config import get_settings


def _fernet_from_secret():
    from cryptography.fernet import Fernet

    secret = get_settings().secret_key.encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    return Fernet(key)


def encrypt_mfa_secret(secret: str) -> str:
    return _fernet_from_secret().encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt_mfa_secret(secret_encrypted: str) -> str:
    return _fernet_from_secret().decrypt(secret_encrypted.encode("utf-8")).decode("utf-8")


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("utf-8").rstrip("=")


def build_totp_uri(*, email: str, secret: str, issuer: str) -> str:
    issuer_enc = quote(issuer)
    account_enc = quote(email)
    return f"otpauth://totp/{issuer_enc}:{account_enc}?secret={secret}&issuer={issuer_enc}&algorithm=SHA1&digits=6&period=30"


def _totp_code(secret: str, counter: int) -> str:
    normalized = secret.upper()
    pad = "=" * ((8 - len(normalized) % 8) % 8)
    key = base64.b32decode(normalized + pad, casefold=True)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 1000000
    return f"{code_int:06d}"


def verify_totp_code(
    secret: str, code: str, *, now: datetime | None = None, window: int = 1
) -> bool:
    if not code or not code.isdigit() or len(code) != 6:
        return False
    ts = int((now or datetime.now(timezone.utc)).timestamp())
    current_counter = ts // 30
    for offset in range(-window, window + 1):
        if hmac.compare_digest(_totp_code(secret, current_counter + offset), code):
            return True
    return False
