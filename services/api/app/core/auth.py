"""Authentication helpers and FastAPI dependencies."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_password
from app.models import User
from app.schemas.auth import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="AccessToken",
)


async def authenticate_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
) -> Optional[User]:
    """Validate user credentials returning the user when successful."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Retrieve the current user from the supplied bearer token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        token_payload = TokenPayload(**payload)
    except (JWTError, ValueError) as exc:
        raise credentials_exception from exc

    if token_payload.type != "access" or token_payload.sub is None:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(token_payload.sub)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    if not user.is_active or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure the current user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


def require_role(*roles: str) -> Callable[[User], User]:
    """Dependency factory enforcing that the user has one of the given roles."""

    async def role_dependency(user: User = Depends(get_current_active_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return role_dependency


async def mark_successful_login(user: User, db: AsyncSession) -> None:
    """Update login metadata on successful authentication."""
    user.last_login_at = datetime.now(timezone.utc)
    user.login_count = (user.login_count or 0) + 1
    user.failed_login_attempts = 0
    await db.flush()


async def register_failed_login(user: Optional[User], db: AsyncSession) -> None:
    """Increment the failed login attempts for a known user."""
    if not user:
        return
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    await db.flush()
