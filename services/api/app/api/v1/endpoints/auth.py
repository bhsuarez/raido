"""Authentication endpoints: login and initial admin setup."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.users import User

router = APIRouter()
logger = structlog.get_logger()

_BCRYPT_MAX_BYTES = 72


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    role: str


class SetupRequest(BaseModel):
    email: str
    password: str
    full_name: str = "Admin"

    @field_validator("password")
    @classmethod
    def password_not_too_long(cls, v: str) -> str:
        if len(v.encode("utf-8")) > _BCRYPT_MAX_BYTES:
            raise ValueError(f"Password must be {_BCRYPT_MAX_BYTES} bytes or fewer")
        return v


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email/password and return a JWT access token."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled")

    # Update login tracking
    user.last_login_at = datetime.now(timezone.utc)
    user.login_count = (user.login_count or 0) + 1
    user.failed_login_attempts = 0
    await db.commit()

    token = create_access_token(user.id)
    logger.info("User logged in", user_id=user.id, email=user.email)
    return LoginResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        role=user.role,
    )


@router.post("/setup", response_model=LoginResponse, status_code=201)
async def setup_admin(payload: SetupRequest, db: AsyncSession = Depends(get_db)):
    """One-time admin account creation. Fails if any user already exists."""
    existing = await db.execute(select(User).limit(1))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Setup already complete. Use /auth/login.",
        )

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role="admin",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    logger.info("Admin account created", email=user.email)
    return LoginResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        role=user.role,
    )


@router.get("/me")
async def get_me(db: AsyncSession = Depends(get_db)):
    """Check if setup is needed (no users exist yet)."""
    result = await db.execute(select(User).limit(1))
    needs_setup = result.scalar_one_or_none() is None
    return {"needs_setup": needs_setup}
