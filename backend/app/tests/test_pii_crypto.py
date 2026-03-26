from importlib import reload


def test_encrypt_decrypt_roundtrip(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("PII_ENCRYPTION_KEYS", "primary:w6vH5hoGVDHhVQmS_mk0n3mKU_GQYfU2y4Ufr6vI7vA=")
    monkeypatch.setenv("PII_ENCRYPTION_ACTIVE_KEY_ID", "primary")
    from app.core.config import get_settings
    from app.core import pii_crypto

    get_settings.cache_clear()
    module = reload(pii_crypto)
    token = module.pii_encrypt("owner@example.com")
    assert token and token.startswith("enc:v1:primary:")
    assert module.pii_decrypt(token) == "owner@example.com"


def test_hash_is_stable():
    from app.core import pii_crypto

    assert pii_crypto.pii_hash("Owner@Example.com") == pii_crypto.pii_hash("owner@example.com")
