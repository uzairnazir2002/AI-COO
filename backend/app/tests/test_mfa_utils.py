from datetime import datetime, timezone

from app.core.mfa import _totp_code, decrypt_mfa_secret, encrypt_mfa_secret, generate_totp_secret, verify_totp_code


def test_encrypt_and_decrypt_round_trip():
    secret = generate_totp_secret()
    encrypted = encrypt_mfa_secret(secret)
    assert encrypted != secret
    assert decrypt_mfa_secret(encrypted) == secret


def test_verify_totp_code_accepts_current_window():
    secret = generate_totp_secret()
    ts = datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc)
    counter = int(ts.timestamp()) // 30
    code = _totp_code(secret, counter)
    assert verify_totp_code(secret, code, now=ts)


def test_verify_totp_code_rejects_invalid_code():
    secret = generate_totp_secret()
    assert verify_totp_code(secret, "000000") is False
