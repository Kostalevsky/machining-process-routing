from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    password = "testpass123"

    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_access_token_roundtrip() -> None:
    token = create_access_token(42)

    payload = decode_access_token(token)

    assert payload["sub"] == "42"
    assert payload["type"] == "access"


def test_refresh_token_roundtrip() -> None:
    token = create_refresh_token(7)

    payload = decode_refresh_token(token)

    assert payload["sub"] == "7"
    assert payload["type"] == "refresh"
