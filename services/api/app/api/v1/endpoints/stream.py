from urllib.parse import urlparse, parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.limiter import limiter
from app.core.security import create_stream_token, validate_stream_token
from app.models.users import User
from app.schemas.stream import StreamStatus

router = APIRouter()


@router.get("/status", response_model=StreamStatus)
async def get_stream_status(db: AsyncSession = Depends(get_db)):
    """Get current stream status"""
    # For now, return mock status
    # In a real implementation, this would query Icecast status
    return StreamStatus(
        is_live=True,
        listeners=0,
        uptime_seconds=3600,
        current_bitrate=128,
        mount_point="/raido.mp3"
    )


@router.get("/token")
async def get_stream_token(current_user: User = Depends(get_current_user)):
    """Issue a short-lived stream token for an authenticated user."""
    token = create_stream_token(user_id=current_user.id)
    return {"token": token, "expires_in": 900}  # 900 seconds = 15 min


@router.get("/guest-token")
@limiter.limit("20/minute")
async def get_guest_stream_token(request: Request):
    """Issue a short-lived stream token for unauthenticated (guest) listeners."""
    token = create_stream_token(user_id=0)
    return {"token": token, "expires_in": settings.STREAM_TOKEN_EXPIRE_MINUTES * 60}


@router.get("/validate")
async def validate_stream(request: Request):
    """Caddy forward_auth endpoint. Reads token from X-Forwarded-Uri query string.

    Returns 200 with X-User-Id header on success, 401 on failure.
    """
    # Caddy sets X-Forwarded-Uri to the original request URI including query string
    forwarded_uri = request.headers.get("X-Forwarded-Uri", "")
    token = None

    if forwarded_uri:
        qs = parse_qs(urlparse(forwarded_uri).query)
        token = qs.get("token", [None])[0]

    if not token:
        # Also check query params directly (for testing without Caddy)
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(status_code=401, detail="Missing stream token")

    payload = validate_stream_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired stream token")

    headers = {"X-User-Id": str(payload.get("user_id", ""))}
    return Response(status_code=200, headers=headers)
