"""Security utilities for password hashing and JWT creation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import uuid4

import bcrypt
from jose import jwt

from app.core.config import settings


def create_access_token(subject: str | int, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    if isinstance(subject, int):
        subject = str(subject)

    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {"sub": subject, "type": "access", "exp": expire}
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: str | int,
    expires_delta: Optional[timedelta] = None,
    jti: Optional[str] = None,
) -> Tuple[str, str]:
    """Create a signed JWT refresh token and return it with its JTI."""
    if isinstance(subject, int):
        subject = str(subject)

    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    token_jti = jti or uuid4().hex
    to_encode = {"sub": subject, "type": "refresh", "jti": token_jti, "exp": expire}
    token = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, token_jti


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Compare a plain password with a stored hash."""
    if not hashed_password:
        return False
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
