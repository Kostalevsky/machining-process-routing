from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    return _encode_token(user_id=user_id, token_type="access", expires_at=expires_at)


def create_refresh_token(user_id: int) -> str:
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_refresh_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return _decode_token(token=token, secret_key=settings.jwt_secret_key, expected_type="access")


def decode_refresh_token(token: str) -> dict:
    return _decode_token(
        token=token,
        secret_key=settings.jwt_refresh_secret_key,
        expected_type="refresh",
    )


def _encode_token(user_id: int, token_type: str, expires_at: datetime) -> str:
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def _decode_token(token: str, secret_key: str, expected_type: str) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials.",
    )

    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
    except jwt.InvalidTokenError as exc:
        raise credentials_exception from exc

    if payload.get("type") != expected_type:
        raise credentials_exception

    if not payload.get("sub"):
        raise credentials_exception

    return payload
