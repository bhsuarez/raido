"""Authentication endpoints: login and initial admin setup."""
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.limiter import limiter
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.users import User

router = APIRouter()
logger = structlog.get_logger()

_BCRYPT_MAX_BYTES = 72


async def _notify_pingos(message: str) -> None:
    """Fire-and-forget Pingos notification. Never raises."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                "http://192.168.1.116:8090/api/notify",
                json={"message": message},
            )
    except Exception as e:
        logger.warning("Pingos notify failed", error=str(e))


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


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str = "Listener"

    @field_validator("password")
    @classmethod
    def password_not_too_long(cls, v: str) -> str:
        if len(v.encode("utf-8")) > _BCRYPT_MAX_BYTES:
            raise ValueError(f"Password must be {_BCRYPT_MAX_BYTES} bytes or fewer")
        return v


class RegisterResponse(BaseModel):
    message: str


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
        if not user.is_verified:
            # Pending approval — different error for the frontend to detect
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="account_pending",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account disabled",
        )

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


@router.post("/register", response_model=RegisterResponse, status_code=201)
@limiter.limit("5/hour")
async def register(payload: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Self-registration. Creates a pending account awaiting admin approval."""
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role="listener",
        is_active=False,
        is_verified=False,
    )
    db.add(user)
    await db.commit()

    logger.info("New registration pending approval", email=payload.email)
    await _notify_pingos(
        f"New Raido registration: {payload.full_name} ({payload.email}) is waiting for approval."
    )

    return RegisterResponse(message="Registration submitted. Pending admin approval.")


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


@router.get("/setup-status")
async def setup_status(db: AsyncSession = Depends(get_db)):
    """Check if initial admin setup is needed (no users exist yet)."""
    result = await db.execute(select(User).limit(1))
    needs_setup = result.scalar_one_or_none() is None
    return {"needs_setup": needs_setup}


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "display_name": current_user.display_name,
        "avatar_url": current_user.avatar_url,
        "role": current_user.role,
        "is_active": current_user.is_active,
    }


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    current_password: str | None = None
    new_password: str | None = None

    @field_validator("new_password")
    @classmethod
    def new_password_not_too_long(cls, v: str | None) -> str | None:
        if v is not None and len(v.encode("utf-8")) > _BCRYPT_MAX_BYTES:
            raise ValueError(f"Password must be {_BCRYPT_MAX_BYTES} bytes or fewer")
        return v


@router.patch("/me")
async def update_me(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's profile (name, avatar, password)."""
    if payload.new_password is not None:
        if not payload.current_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="current_password is required to set a new password")
        if not verify_password(payload.current_password, current_user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
        current_user.hashed_password = get_password_hash(payload.new_password)

    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.display_name is not None:
        current_user.display_name = payload.display_name or None
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url or None

    await db.commit()
    await db.refresh(current_user)

    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "display_name": current_user.display_name,
        "avatar_url": current_user.avatar_url,
        "role": current_user.role,
    }
