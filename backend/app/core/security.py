"""
Security primitives
===================
JWT creation / verification and bcrypt password helpers.

All API route files should import auth dependencies from core.dependencies,
which in turn uses these low-level functions.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# ── Constants ─────────────────────────────────────────────────────────────────

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Shared OAuth2 bearer scheme used by all protected endpoints.
# Import this from here rather than re-defining it in each router.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login"
)
oauth2_optional = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,
)

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password helpers ──────────────────────────────────────────────────────────

def get_password_hash(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return _pwd.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the stored bcrypt *hashed* string."""
    return _pwd.verify(plain, hashed)


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT.

    Parameters
    ----------
    data          : Payload dict — must include ``"sub"`` (user UUID as str).
    expires_delta : Override default 24-hour expiry.

    Returns
    -------
    Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict[str, Any] | None:
    """
    Decode and verify a JWT.

    Returns the payload dict on success, or ``None`` if the token is
    expired, tampered, or otherwise invalid.  Never raises.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
