import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import get_settings


_PREFIX = "enc:v1:"


def _load_keyring() -> dict[str, Fernet]:
    settings = get_settings()
    raw = (settings.pii_encryption_keys or "").strip()
    if not raw:
        return {}
    pairs = [item.strip() for item in raw.split(",") if item.strip()]
    keyring: dict[str, Fernet] = {}
    for pair in pairs:
        kid, _, value = pair.partition(":")
        if not kid or not value:
            continue
        keyring[kid.strip()] = Fernet(value.strip().encode("utf-8"))
    return keyring


def _active_fernet() -> tuple[str, Fernet] | None:
    settings = get_settings()
    keyring = _load_keyring()
    if not keyring:
        return None
    kid = settings.pii_encryption_active_key_id
    if kid in keyring:
        return kid, keyring[kid]
    first_kid = next(iter(keyring.keys()))
    return first_kid, keyring[first_kid]


def pii_encrypt(value: str | None) -> str | None:
    if value is None:
        return None
    active = _active_fernet()
    if active is None:
        return value
    kid, f = active
    token = f.encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{_PREFIX}{kid}:{token}"


def pii_decrypt(value: str | None) -> str | None:
    if value is None:
        return None
    if not value.startswith(_PREFIX):
        return value
    keyring = _load_keyring()
    rest = value[len(_PREFIX) :]
    kid, _, token = rest.partition(":")
    f = keyring.get(kid)
    if not f:
        return value
    try:
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
    except Exception:
        return value


def pii_reencrypt(value: str | None) -> str | None:
    if value is None:
        return None
    plain = pii_decrypt(value)
    return pii_encrypt(plain)


def pii_hash(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def active_pii_key_id() -> str:
    active = _active_fernet()
    if active is None:
        return "plaintext"
    return active[0]


def generate_pii_key() -> str:
    return base64.urlsafe_b64encode(Fernet.generate_key()).decode("utf-8")
