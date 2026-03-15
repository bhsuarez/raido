# Raido Listener Role Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.


> **Implementation status:** COMPLETE — all code was implemented prior to this planning session. This document serves as the design record.

**Goal:** Add a self-registration+approval listener role, Caddy forward_auth stream gating with short-lived tokens, IP-based listener session tracking, and admin analytics pages.

**Architecture:** Short-lived stream tokens (signed JWT, 15-min TTL, separate `STREAM_TOKEN_SECRET`) are issued to authenticated users and validated by Caddy's `forward_auth` before proxying Icecast. Listener sessions are tracked via 30s heartbeat pings in a new `listener_sessions` PostgreSQL table; a background task closes stale sessions after 90s of no heartbeat. GeoIP lookup uses MaxMind GeoLite2-City DB.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, PostgreSQL, `geoip2`, `slowapi`, `user-agents`, `python-jose`, React/TypeScript, Zustand, Caddy, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-03-14-raido-listener-role-design.md`

---

## File Map

### New files
| File | Purpose |
|------|---------|
| `services/api/app/models/listener_session.py` | ListenerSession SQLAlchemy model |
| `services/api/app/schemas/listener.py` | Pydantic schemas for sessions + user mgmt |
| `services/api/app/core/geoip.py` | GeoIP lookup utility (graceful degradation) |
| `services/api/app/core/limiter.py` | Shared slowapi Limiter instance (avoids duplicate instances) |
| `services/api/alembic/versions/010_add_listener_sessions.py` | DB migration |
| `services/api/app/api/v1/endpoints/listeners.py` | Session CRUD endpoints |
| `web/src/components/RequireAuth.tsx` | Route guard: redirect to /login if unauthenticated |
| `web/src/components/RequireAdmin.tsx` | Route guard: redirect to / if role != admin |
| `web/src/components/RegisterPage.tsx` | Self-registration form |
| `web/src/components/admin/UserManagement.tsx` | User approval queue + user table |
| `web/src/components/admin/ListenerSessions.tsx` | Active sessions + session history |

### Modified files
| File | Change |
|------|--------|
| `services/api/requirements.txt` | Add `slowapi`, `geoip2`, `user-agents` |
| `services/api/app/core/config.py` | Add `STREAM_TOKEN_SECRET`, `GEOIP_DB_PATH` |
| `services/api/app/models/__init__.py` | Export `ListenerSession` |
| `services/api/app/api/v1/endpoints/auth.py` | Add register, setup-status; fix me, login |
| `services/api/app/api/v1/endpoints/stream.py` | Add token + validate endpoints |
| `services/api/app/api/v1/endpoints/admin.py` | Add user mgmt + listener analytics |
| `services/api/app/api/v1/__init__.py` | Include listeners router |
| `services/api/app/main.py` | Add stale session background task |
| `infra/Caddyfile` | Add forward_auth to /stream/* in main + :80 blocks |
| `docker-compose.yml` | Remove Icecast port 8000 host mapping |
| `web/src/App.tsx` | Add RequireAuth/RequireAdmin, new routes |
| `web/src/components/Layout.tsx` | Role-based nav, fix stream link |
| `web/src/components/LoginPage.tsx` | Register mode, pending message, setup-status |
| `web/src/components/RadioPlayer.tsx` | Stream token fetch + session tracking |

---

## Chunk 1: Database & Config Foundation

### Task 1: Add Python dependencies

**Files:**
- Modify: `services/api/requirements.txt`

- [ ] **Step 1: Add new dependencies**

```text
# append to services/api/requirements.txt
slowapi==0.1.9
geoip2==4.8.0
user-agents==2.2.0
```

- [ ] **Step 2: Rebuild the API container to verify dependencies install cleanly**

```bash
docker compose build api 2>&1 | tail -20
```
Expected: `Successfully built` with no pip errors.

- [ ] **Step 3: Commit**

```bash
git add services/api/requirements.txt
git commit -m "chore: add slowapi, geoip2, user-agents dependencies"
```

---

### Task 2: Add config vars

**Files:**
- Modify: `services/api/app/core/config.py`

- [ ] **Step 1: Add the two new settings to the `Settings` class after the `SESSION_SECRET` line**

Add inside the `Settings` class, in the `# Security` section:
```python
    STREAM_TOKEN_SECRET: str  # No default — app fails to start if missing
    STREAM_TOKEN_EXPIRE_MINUTES: int = 15
    GEOIP_DB_PATH: str = "/app/geoip/GeoLite2-City.mmdb"
```

- [ ] **Step 2: Add placeholder to `.env` (if it exists) so the app starts locally**

```bash
# In services/api/.env or the root .env, add:
STREAM_TOKEN_SECRET=dev-stream-secret-change-in-production
```

- [ ] **Step 3: Verify the app starts with the new required var**

```bash
docker compose up api --no-deps -d && sleep 3 && docker compose logs api | tail -10
```
Expected: `Raido API starting up` without `ValidationError`.

- [ ] **Step 4: Commit**

```bash
git add services/api/app/core/config.py
git commit -m "feat: add STREAM_TOKEN_SECRET and GEOIP_DB_PATH config vars"
```

---

### Task 3: GeoIP utility

**Files:**
- Create: `services/api/app/core/geoip.py`

- [ ] **Step 1: Write the unit test first**

Create `services/api/tests/test_geoip.py`:
```python
"""Unit tests for GeoIP lookup utility."""
import pytest
from unittest.mock import patch, MagicMock
from app.core.geoip import lookup_ip, GeoResult


def test_private_ip_returns_none():
    result = lookup_ip("192.168.1.1")
    assert result is None


def test_none_ip_returns_none():
    result = lookup_ip(None)
    assert result is None


def test_successful_lookup():
    mock_response = MagicMock()
    mock_response.city.name = "Chicago"
    mock_response.subdivisions.most_specific.name = "Illinois"
    mock_response.country.name = "United States"
    mock_response.country.iso_code = "US"
    mock_response.location.latitude = 41.8781
    mock_response.location.longitude = -87.6298

    with patch("app.core.geoip._reader") as mock_reader:
        mock_reader.city.return_value = mock_response
        result = lookup_ip("8.8.8.8")

    assert result is not None
    assert result.city == "Chicago"
    assert result.country_code == "US"
    assert result.latitude == pytest.approx(41.8781)


def test_db_not_found_returns_none():
    with patch("app.core.geoip._reader", None), patch("app.core.geoip._reader_tried", True):
        result = lookup_ip("8.8.8.8")
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails (no implementation yet)**

```bash
docker compose exec api python -m pytest tests/test_geoip.py -v 2>&1 | tail -20
```
Expected: `ImportError` or `ModuleNotFoundError` for `app.core.geoip`.

- [ ] **Step 3: Implement the GeoIP utility**

Create `services/api/app/core/geoip.py`:
```python
"""GeoIP lookup using MaxMind GeoLite2-City database.

Gracefully degrades: returns None if the DB file is missing, the IP is
private/reserved, or any other lookup error occurs.
"""
from __future__ import annotations

import ipaddress
import logging
from dataclasses import dataclass
from typing import Optional

import structlog

logger = structlog.get_logger()

_reader = None          # Module-level reader, initialized lazily
_reader_tried = False   # Sentinel: True after first init attempt (success or fail)


def _get_reader():
    """Lazily initialize the geoip2 reader. Returns None if DB unavailable.

    Uses _reader_tried so the "DB not available" warning is only logged once,
    not on every lookup when the DB is absent.
    """
    global _reader, _reader_tried
    if _reader_tried:
        return _reader
    _reader_tried = True
    try:
        import geoip2.database
        from app.core.config import settings
        _reader = geoip2.database.Reader(settings.GEOIP_DB_PATH)
        logger.info("GeoIP database loaded", path=settings.GEOIP_DB_PATH)
    except Exception as e:
        logger.warning("GeoIP database not available", error=str(e))
        _reader = None
    return _reader


@dataclass
class GeoResult:
    city: Optional[str]
    region: Optional[str]
    country: Optional[str]
    country_code: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]


def lookup_ip(ip: Optional[str]) -> Optional[GeoResult]:
    """Look up approximate location for an IP address.

    Returns None for private IPs, missing DB, or any lookup failure.
    """
    if not ip:
        return None

    try:
        addr = ipaddress.ip_address(ip)
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            return None
    except ValueError:
        return None

    reader = _get_reader()
    if reader is None:
        return None

    try:
        response = reader.city(ip)
        return GeoResult(
            city=response.city.name or None,
            region=response.subdivisions.most_specific.name or None,
            country=response.country.name or None,
            country_code=response.country.iso_code or None,
            latitude=response.location.latitude,
            longitude=response.location.longitude,
        )
    except Exception as e:
        logger.debug("GeoIP lookup failed", ip=ip, error=str(e))
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose exec api python -m pytest tests/test_geoip.py -v 2>&1 | tail -20
```
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add services/api/app/core/geoip.py services/api/tests/test_geoip.py
git commit -m "feat: add GeoIP lookup utility with graceful degradation"
```

---

### Task 4: ListenerSession model

**Files:**
- Create: `services/api/app/models/listener_session.py`
- Modify: `services/api/app/models/__init__.py`

- [ ] **Step 1: Create the model**

Create `services/api/app/models/listener_session.py`:
```python
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class ListenerSession(Base):
    __tablename__ = "listener_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    station = Column(String(100), nullable=False, default="main")

    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_heartbeat_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True, index=True)
    duration_seconds = Column(Integer, nullable=True)  # written on session close

    # Location
    ip_address = Column(String(45), nullable=True)
    city = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    country_code = Column(String(2), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Device metadata
    user_agent = Column(Text, nullable=True)
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    device_type = Column(String(20), nullable=True)  # mobile, tablet, desktop

    user = relationship("User", back_populates=None)

    def __repr__(self):
        return f"<ListenerSession(id={self.id}, user_id={self.user_id}, station='{self.station}')>"
```

- [ ] **Step 2: Export from models `__init__.py`**

In `services/api/app/models/__init__.py`, add:
```python
from .listener_session import ListenerSession
```
And add `"ListenerSession"` to `__all__`.

- [ ] **Step 3: Commit**

```bash
git add services/api/app/models/listener_session.py services/api/app/models/__init__.py
git commit -m "feat: add ListenerSession SQLAlchemy model"
```

---

### Task 5: Alembic migration

**Files:**
- Create: `services/api/alembic/versions/010_add_listener_sessions.py`

- [ ] **Step 1: Check for multiple Alembic heads before creating migration**

```bash
docker compose exec api alembic heads
```
If there are 2 heads (the branched `056a5f22cfdb`), merge them first:
```bash
docker compose exec api alembic merge heads -m "merge_branches"
# Then the migration number becomes 011 — update accordingly
```
If there is 1 head (the branch was already merged), proceed to create `010`.

- [ ] **Step 2: Create the migration**

```bash
docker compose exec api alembic revision --autogenerate -m "add_listener_sessions"
```

Then edit the generated file to verify it includes the correct `listener_sessions` table. The file will be in `services/api/alembic/versions/`. Confirm it has:
- All columns from the model (`id`, `user_id`, `station`, `started_at`, `last_heartbeat_at`, `ended_at`, `duration_seconds`, `ip_address`, `city`, `region`, `country`, `country_code`, `latitude`, `longitude`, `user_agent`, `browser`, `os`, `device_type`)
- Index on `user_id`
- Index on `ended_at`
- FK to `users.id`

- [ ] **Step 3: Run the migration**

```bash
docker compose exec api alembic upgrade head
```
Expected: `Running upgrade ... -> <revision>` with no errors.

- [ ] **Step 4: Verify table exists**

```bash
docker compose exec api python -c "
import asyncio
from app.core.database import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        r = await conn.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name='listener_sessions'\"))
        print([row[0] for row in r])

asyncio.run(check())
"
```
Expected: list of all column names.

- [ ] **Step 5: Commit**

```bash
git add services/api/alembic/versions/
git commit -m "feat: add listener_sessions table migration"
```

---

## Chunk 2: Auth Backend

### Task 6: Registration endpoint + Pingos notify

**Files:**
- Modify: `services/api/app/api/v1/endpoints/auth.py`

- [ ] **Step 1: Write the test**

Create `services/api/tests/test_auth_register.py`:
```python
"""Tests for the registration endpoint."""
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from app.main import app


@pytest.mark.anyio
async def test_register_creates_pending_user():
    """New registrations should create inactive, unverified users."""
    with patch("app.api.v1.endpoints.auth._notify_pingos", AsyncMock()):
        async with AsyncClient(app=app, base_url="http://test") as client:
            resp = await client.post("/api/v1/auth/register", json={
                "email": "friend@example.com",
                "password": "securepassword",
                "full_name": "Alice Friend",
            })
    # Will fail initially since register endpoint doesn't exist yet
    assert resp.status_code == 201
    data = resp.json()
    assert data["message"] == "Registration submitted. Pending admin approval."


@pytest.mark.anyio
@pytest.mark.skip(reason="requires a pre-existing user in DB — implement after basic register works")
async def test_register_duplicate_email_returns_409():
    """Registering with an existing email returns 409."""
    pass
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker compose exec api python -m pytest tests/test_auth_register.py::test_register_creates_pending_user -v 2>&1 | tail -15
```
Expected: `404` or connection error (endpoint doesn't exist yet).

- [ ] **Step 3: Add imports and helper to `auth.py`**

At the top of `services/api/app/api/v1/endpoints/auth.py`, add:
```python
import httpx
from app.core.security import get_password_hash
```

Add Pydantic models after existing ones:
```python
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
```

Add the Pingos notify helper after the logger line:
```python
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
```

- [ ] **Step 4: Add the register endpoint**

```python
@router.post("/register", response_model=RegisterResponse, status_code=201)
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
```

Note: Add `from fastapi import Request` to the imports at the top of `auth.py`. The `request: Request` parameter is needed by slowapi's rate limiter (added in Task 7).

- [ ] **Step 5: Run test to verify it passes**

```bash
docker compose exec api python -m pytest tests/test_auth_register.py::test_register_creates_pending_user -v 2>&1 | tail -15
```
Expected: `1 passed`.

- [ ] **Step 6: Commit**

```bash
git add services/api/app/api/v1/endpoints/auth.py services/api/tests/test_auth_register.py
git commit -m "feat: add /auth/register endpoint with Pingos notification"
```

---

### Task 7: Rate limit registration

**Files:**
- Create: `services/api/app/core/limiter.py`
- Modify: `services/api/app/api/v1/endpoints/auth.py`
- Modify: `services/api/app/main.py`

> **Why a shared module:** `slowapi` requires a single `Limiter` instance shared between the decorator and the exception handler registered on the FastAPI app. Creating two instances (one in `main.py`, one in `auth.py`) causes the 429 handler to never fire and produces a 500 instead. The fix is one shared module imported by both.

- [ ] **Step 1: Create `services/api/app/core/limiter.py`**

```python
"""Shared slowapi rate limiter instance.

Import this module everywhere rate limiting decorators or middleware are needed.
Creating multiple Limiter instances causes the exception handler to mismatch.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
```

- [ ] **Step 2: Wire middleware into main.py**

In `services/api/app/main.py`, add after the existing imports:
```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter
```

After creating `app = FastAPI(...)`, add:
```python
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

- [ ] **Step 3: Apply rate limit to register endpoint**

In `auth.py`, import from the shared module:
```python
from app.core.limiter import limiter
```

Decorate the register endpoint. **`@limiter.limit` must be outermost — place it above `@router.post`:**
```python
@limiter.limit("5/hour")
@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(payload: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ...
```

- [ ] **Step 4: Restart API and verify rate limiting works**

```bash
docker compose restart api && sleep 3
# Hit register 6 times quickly:
for i in $(seq 1 6); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost/api/v1/auth/register \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"test$i@example.com\",\"password\":\"pass\",\"full_name\":\"Test\"}"
done
```
Expected: First 5 return `201` or `409`, 6th returns `429`.

- [ ] **Step 5: Commit**

```bash
git add services/api/app/core/limiter.py services/api/app/main.py services/api/app/api/v1/endpoints/auth.py
git commit -m "feat: rate-limit /auth/register to 5 requests/hour per IP"
```

---

### Task 8: Fix login (pending vs suspended distinction)

**Files:**
- Modify: `services/api/app/api/v1/endpoints/auth.py`

- [ ] **Step 1: Update the login handler**

Replace the current `if not user.is_active:` block in the login endpoint with:
```python
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
```

- [ ] **Step 2: Verify manually**

```bash
# Create a pending user first, then try to log in:
curl -s -X POST http://localhost/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"pending@test.com","password":"testpass","full_name":"Pending User"}'

# Now try to log in as them:
curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"pending@test.com","password":"testpass"}'
```
Expected: `{"detail": "account_pending"}` with HTTP 403.

- [ ] **Step 3: Commit**

```bash
git add services/api/app/api/v1/endpoints/auth.py
git commit -m "fix: distinguish pending users (403) from suspended (401) on login"
```

---

### Task 9: Add /auth/setup-status and fix /auth/me

**Files:**
- Modify: `services/api/app/api/v1/endpoints/auth.py`

- [ ] **Step 1: Replace the existing `get_me` function in `auth.py`**

The existing `GET /me` route (function `get_me`) does a setup-check. We need to:
1. Add a new `setup_status` function on the `/setup-status` path
2. **Remove (or replace) the existing `get_me` function entirely** — do not leave both registered or FastAPI will use one silently
3. Add a new `get_me` that returns the user profile

In `auth.py`, **delete the existing `get_me` function and its `@router.get("/me")` decorator**, then add:
```python
@router.get("/setup-status")
async def setup_status(db: AsyncSession = Depends(get_db)):
    """Check if initial admin setup is needed (no users exist yet)."""
    result = await db.execute(select(User).limit(1))
    needs_setup = result.scalar_one_or_none() is None
    return {"needs_setup": needs_setup}
```

- [ ] **Step 2: Add the new `/auth/me` that returns the current user profile**

```python
from app.core.deps import get_current_user


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
    }
```

- [ ] **Step 3: Verify both endpoints work**

```bash
# Setup status (no auth required):
curl -s http://localhost/api/v1/auth/setup-status | python3 -m json.tool
# Expected: {"needs_setup": false}

# Verify /me no longer returns setup-check (must return 401 without token):
curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v1/auth/me
# Expected: 401 (not {"needs_setup": ...})

# /me with a valid token — use your admin token:
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"yourpassword"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s http://localhost/api/v1/auth/me -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
# Expected: {"id": ..., "email": ..., "role": "admin", "is_active": true, ...}
```

- [ ] **Step 4: Commit**

```bash
git add services/api/app/api/v1/endpoints/auth.py
git commit -m "feat: add /auth/setup-status; fix /auth/me to return user profile"
```

---

### Task 10: Stream token endpoints

**Files:**
- Modify: `services/api/app/api/v1/endpoints/stream.py`
- Modify: `services/api/app/core/security.py`

- [ ] **Step 1: Write unit tests for stream token functions**

Create `services/api/tests/test_stream_token.py`:
```python
"""Unit tests for stream token creation and validation."""
import pytest
from datetime import timedelta
from app.core.security import create_stream_token, validate_stream_token


def test_create_and_validate_stream_token():
    token = create_stream_token(user_id=42)
    payload = validate_stream_token(token)
    assert payload is not None
    assert payload["user_id"] == 42
    assert payload["type"] == "stream"


def test_expired_stream_token_returns_none():
    token = create_stream_token(user_id=1, expires_delta=timedelta(seconds=-1))
    result = validate_stream_token(token)
    assert result is None


def test_main_jwt_rejected_as_stream_token():
    """A regular access token must not be accepted as a stream token."""
    from app.core.security import create_access_token
    access_token = create_access_token(subject=1)
    result = validate_stream_token(access_token)
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose exec api python -m pytest tests/test_stream_token.py -v 2>&1 | tail -15
```
Expected: `ImportError` for `create_stream_token`.

- [ ] **Step 3: Add stream token functions to security.py**

In `services/api/app/core/security.py`, add after `create_refresh_token`:
```python
def create_stream_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """Create a short-lived stream token signed with STREAM_TOKEN_SECRET."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.STREAM_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"user_id": user_id, "type": "stream", "exp": expire}
    return jwt.encode(payload, settings.STREAM_TOKEN_SECRET, algorithm=settings.JWT_ALGORITHM)


def validate_stream_token(token: str) -> Optional[dict]:
    """Validate a stream token. Returns payload dict or None if invalid/expired."""
    try:
        payload = jwt.decode(token, settings.STREAM_TOKEN_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "stream":
            return None
        return payload
    except Exception:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose exec api python -m pytest tests/test_stream_token.py -v 2>&1 | tail -15
```
Expected: `3 passed`.

- [ ] **Step 5: Read current stream.py before editing**

```bash
cat services/api/app/api/v1/endpoints/stream.py
```
Confirm the current content, then add the two new endpoints **below** the existing `get_stream_status` endpoint. Do **not** replace the file — only append.

- [ ] **Step 6: Add stream token endpoints to stream.py**

Add the following imports at the top of `stream.py` (after existing imports):
```python
from fastapi import Request
from app.core.deps import get_current_user
from app.core.security import create_stream_token, validate_stream_token
from app.models.users import User
```

Then append the two new endpoints **after** the existing `get_stream_status` function:
```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_stream_token, validate_stream_token
from app.models.users import User
from app.schemas.stream import StreamStatus

router = APIRouter()


@router.get("/status", response_model=StreamStatus)
async def get_stream_status(db: AsyncSession = Depends(get_db)):
    """Get current stream status."""
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


@router.get("/validate")
async def validate_stream(request: Request):
    """Caddy forward_auth endpoint. Reads token from X-Forwarded-Uri query string.

    Returns 200 with X-User-Id header on success, 401 on failure.
    """
    from fastapi.responses import Response

    from urllib.parse import urlparse, parse_qs

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

    headers = {"X-User-Id": str(payload["user_id"])}
    return Response(status_code=200, headers=headers)
```

- [ ] **Step 7: Verify token endpoint works**

```bash
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"yourpassword"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

STREAM_TOKEN=$(curl -s http://localhost/api/v1/stream/token \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Validate it:
curl -s -o /dev/null -w "%{http_code}" "http://localhost/api/v1/stream/validate?token=$STREAM_TOKEN"
```
Expected: `200`.

- [ ] **Step 8: Commit**

```bash
git add services/api/app/core/security.py services/api/app/api/v1/endpoints/stream.py services/api/tests/test_stream_token.py
git commit -m "feat: add stream token creation, validation, and API endpoints"
```

---

## Chunk 3: Listener Session Tracking Backend

### Task 11: Listener session schemas

**Files:**
- Create: `services/api/app/schemas/listener.py`

- [ ] **Step 1: Create the schema file**

Create `services/api/app/schemas/listener.py`:
```python
"""Pydantic schemas for listener sessions."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SessionStartRequest(BaseModel):
    station: str = "main"


class SessionStartResponse(BaseModel):
    session_id: int
    message: str = "Session started"


class SessionHeartbeatResponse(BaseModel):
    ok: bool = True


class SessionEndResponse(BaseModel):
    duration_seconds: Optional[int]


class ListenerSessionRead(BaseModel):
    id: int
    user_id: int
    station: str
    started_at: datetime
    last_heartbeat_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: Optional[int]
    city: Optional[str]
    region: Optional[str]
    country: Optional[str]
    country_code: Optional[str]
    browser: Optional[str]
    os: Optional[str]
    device_type: Optional[str]

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Commit**

```bash
git add services/api/app/schemas/listener.py
git commit -m "feat: add listener session Pydantic schemas"
```

---

### Task 12: Listener session CRUD endpoints

**Files:**
- Create: `services/api/app/api/v1/endpoints/listeners.py`
- Modify: `services/api/app/api/v1/__init__.py`

- [ ] **Step 1: Create the listeners endpoint module**

Create `services/api/app/api/v1/endpoints/listeners.py`:
```python
"""Listener session tracking endpoints."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.geoip import lookup_ip
from app.models.listener_session import ListenerSession
from app.models.users import User
from app.schemas.listener import (
    SessionStartRequest,
    SessionStartResponse,
    SessionHeartbeatResponse,
    SessionEndResponse,
)

router = APIRouter()
logger = structlog.get_logger()


def _parse_user_agent(ua_string: Optional[str]) -> dict:
    """Parse user agent string into browser/os/device_type."""
    if not ua_string:
        return {"browser": None, "os": None, "device_type": "desktop"}
    try:
        import user_agents
        ua = user_agents.parse(ua_string)
        device_type = "mobile" if ua.is_mobile else ("tablet" if ua.is_tablet else "desktop")
        return {
            "browser": ua.browser.family or None,
            "os": ua.os.family or None,
            "device_type": device_type,
        }
    except Exception:
        return {"browser": None, "os": None, "device_type": "desktop"}


@router.post("/sessions", response_model=SessionStartResponse, status_code=201)
async def start_session(
    payload: SessionStartRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a new listener session. Geolocates IP and parses user agent."""
    # Close any existing open sessions for this user (station switch or reconnect)
    now = datetime.now(timezone.utc)
    existing = await db.execute(
        select(ListenerSession).where(
            and_(ListenerSession.user_id == current_user.id, ListenerSession.ended_at.is_(None))
        )
    )
    for session in existing.scalars().all():
        started = session.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        elapsed = (now - started).total_seconds()
        session.ended_at = now
        session.duration_seconds = int(elapsed)

    # Get client IP (behind Caddy proxy)
    ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else None)
    if ip and "," in ip:
        ip = ip.split(",")[0].strip()

    geo = lookup_ip(ip)
    ua_str = request.headers.get("User-Agent")
    ua_info = _parse_user_agent(ua_str)

    session = ListenerSession(
        user_id=current_user.id,
        station=payload.station,
        ip_address=ip,
        city=geo.city if geo else None,
        region=geo.region if geo else None,
        country=geo.country if geo else None,
        country_code=geo.country_code if geo else None,
        latitude=geo.latitude if geo else None,
        longitude=geo.longitude if geo else None,
        user_agent=ua_str,
        browser=ua_info["browser"],
        os=ua_info["os"],
        device_type=ua_info["device_type"],
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info("Listener session started", user_id=current_user.id, station=payload.station)
    return SessionStartResponse(session_id=session.id)


@router.post("/sessions/{session_id}/heartbeat", response_model=SessionHeartbeatResponse)
async def heartbeat(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update last_heartbeat_at for an active session."""
    result = await db.execute(
        select(ListenerSession).where(ListenerSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your session")
    if session.ended_at is not None:
        raise HTTPException(status_code=410, detail="Session already ended")

    session.last_heartbeat_at = datetime.now(timezone.utc)
    await db.commit()
    return SessionHeartbeatResponse()


@router.post("/sessions/{session_id}/end", response_model=SessionEndResponse)
async def end_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Explicitly end a session and record final duration."""
    result = await db.execute(
        select(ListenerSession).where(ListenerSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your session")
    if session.ended_at is not None:
        return SessionEndResponse(duration_seconds=session.duration_seconds)

    now = datetime.now(timezone.utc)
    started = session.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    session.ended_at = now
    session.duration_seconds = int((now - started).total_seconds())
    await db.commit()

    logger.info("Listener session ended", session_id=session_id, duration=session.duration_seconds)
    return SessionEndResponse(duration_seconds=session.duration_seconds)
```

- [ ] **Step 2: Register the router in `__init__.py`**

In `services/api/app/api/v1/__init__.py`, add:
```python
from app.api.v1.endpoints import listeners
```
And add:
```python
api_router.include_router(listeners.router, prefix="/listeners", tags=["listeners"])
```

- [ ] **Step 3: Verify endpoints are reachable**

```bash
docker compose restart api && sleep 3
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"yourpassword"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Start a session:
SESSION=$(curl -s -X POST http://localhost/api/v1/listeners/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"station":"main"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

echo "Session ID: $SESSION"

# Heartbeat:
curl -s -X POST http://localhost/api/v1/listeners/sessions/$SESSION/heartbeat \
  -H "Authorization: Bearer $TOKEN"

# End:
curl -s -X POST http://localhost/api/v1/listeners/sessions/$SESSION/end \
  -H "Authorization: Bearer $TOKEN"
```
Expected: Session created, heartbeat returns `{"ok":true}`, end returns `{"duration_seconds": N}`.

- [ ] **Step 4: Commit**

```bash
git add services/api/app/api/v1/endpoints/listeners.py services/api/app/api/v1/__init__.py
git commit -m "feat: add listener session CRUD endpoints (start, heartbeat, end)"
```

---

### Task 13: Stale session background task

**Files:**
- Modify: `services/api/app/main.py`

- [ ] **Step 1: Add the stale session cleanup task**

In `services/api/app/main.py`, add after the existing background task functions:

```python
async def _close_stale_listener_sessions():
    """Close listener sessions with no heartbeat in the last 90 seconds.

    Runs every 60 seconds. A session is stale when last_heartbeat_at is
    more than 90 seconds ago and ended_at is still NULL.
    """
    from sqlalchemy import update
    from sqlalchemy.sql import func as sqlfunc
    from app.core.database import AsyncSessionLocal
    from app.models.listener_session import ListenerSession

    while True:
        await asyncio.sleep(60)
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(seconds=90)
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ListenerSession).where(
                        and_(
                            ListenerSession.ended_at.is_(None),
                            ListenerSession.last_heartbeat_at < cutoff,
                        )
                    )
                )
                stale = result.scalars().all()
                for session in stale:
                    lhb = session.last_heartbeat_at
                    if lhb.tzinfo is None:
                        lhb = lhb.replace(tzinfo=timezone.utc)
                    started = session.started_at
                    if started.tzinfo is None:
                        started = started.replace(tzinfo=timezone.utc)
                    session.ended_at = lhb
                    session.duration_seconds = int((lhb - started).total_seconds())
                if stale:
                    await db.commit()
                    logger.info("Closed stale listener sessions", count=len(stale))
        except Exception as e:
            logger.warning("Stale session cleanup failed", error=str(e))
```

Add at the top of main.py where other datetime imports are:
```python
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_
```

In the `lifespan` function, add the task alongside existing background tasks:
```python
    asyncio.create_task(_close_stale_listener_sessions())
```

- [ ] **Step 2: Restart and verify the task starts**

```bash
docker compose restart api && sleep 5
docker compose logs api | grep -i "stale\|session" | head -5
```
Expected: No errors. The stale cleanup runs every 60s silently unless sessions are found.

- [ ] **Step 3: Commit**

```bash
git add services/api/app/main.py
git commit -m "feat: add background task to close stale listener sessions after 90s"
```

---

## Chunk 4: Admin Backend

### Task 14: User management endpoints

**Files:**
- Modify: `services/api/app/api/v1/endpoints/admin.py`

- [ ] **Step 1: Add user management endpoints to admin.py**

At the end of `services/api/app/api/v1/endpoints/admin.py`, add:

```python
# ─── User Management ────────────────────────────────────────────────────────

from app.core.deps import require_admin
from app.models.users import User
from app.core.security import get_password_hash


class AdminCreateUserRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""
    role: str = "listener"


class AdminUserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    last_login_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/users", tags=["admin-users"])
async def list_users(
    status: Optional[str] = Query(None, description="pending | active | suspended"),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List users. Filter by status: pending (inactive+unverified), active, suspended (inactive+verified)."""
    q = select(User).where(User.deleted_at.is_(None))

    if status == "pending":
        q = q.where(User.is_active == False, User.is_verified == False)
    elif status == "active":
        q = q.where(User.is_active == True)
    elif status == "suspended":
        q = q.where(User.is_active == False, User.is_verified == True)

    result = await db.execute(q.order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [AdminUserResponse.model_validate(u) for u in users]


@router.post("/users", status_code=201, tags=["admin-users"])
async def create_user(
    payload: AdminCreateUserRequest,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin creates a user directly (no approval needed)."""
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already in use")

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return AdminUserResponse.model_validate(user)


@router.post("/users/{user_id}/approve", tags=["admin-users"])
async def approve_user(
    user_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approve a pending registration."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    user.is_verified = True
    await db.commit()
    return {"ok": True, "user_id": user_id}


@router.post("/users/{user_id}/suspend", tags=["admin-users"])
async def suspend_user(
    user_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Suspend an active user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    await db.commit()
    return {"ok": True, "user_id": user_id}


@router.delete("/users/{user_id}", tags=["admin-users"])
async def delete_user(
    user_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.deleted_at = datetime.now(timezone.utc)
    user.is_active = False
    await db.commit()
    return {"ok": True}
```

Add `from datetime import datetime, timezone` and `from typing import Optional` to the imports at the top of admin.py if not already present. Also add `from pydantic import BaseModel`.

- [ ] **Step 2: Verify endpoints work**

```bash
docker compose restart api && sleep 3
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"yourpassword"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# List pending users:
curl -s "http://localhost/api/v1/admin/users?status=pending" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```
Expected: JSON array of pending users.

- [ ] **Step 3: Commit**

```bash
git add services/api/app/api/v1/endpoints/admin.py
git commit -m "feat: add admin user management endpoints (list, approve, suspend, delete)"
```

---

### Task 15: Listener analytics endpoints

**Files:**
- Modify: `services/api/app/api/v1/endpoints/admin.py`

- [ ] **Step 1: Add listener analytics endpoints to admin.py**

```python
# ─── Listener Analytics ──────────────────────────────────────────────────────

from app.models.listener_session import ListenerSession
from app.schemas.listener import ListenerSessionRead


@router.get("/listener-sessions/active", tags=["admin-listeners"])
async def get_active_sessions(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Return currently active listener sessions (heartbeat within 90s)."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=90)
    result = await db.execute(
        select(ListenerSession, User.email, User.full_name)
        .join(User, ListenerSession.user_id == User.id)
        .where(
            ListenerSession.ended_at.is_(None),
            ListenerSession.last_heartbeat_at >= cutoff,
        )
        .order_by(ListenerSession.started_at.desc())
    )
    rows = result.all()
    sessions = []
    now = datetime.now(timezone.utc)
    for session, email, full_name in rows:
        started = session.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        sessions.append({
            **ListenerSessionRead.model_validate(session).model_dump(),
            "user_email": email,
            "user_name": full_name,
            "current_duration_seconds": int((now - started).total_seconds()),
        })
    return sessions


@router.get("/listener-sessions/summary", tags=["admin-listeners"])
async def get_listener_summary(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Per-user listening summary: total duration, session count, last seen."""
    from sqlalchemy import func as sqlfunc
    result = await db.execute(
        select(
            User.id,
            User.email,
            User.full_name,
            sqlfunc.count(ListenerSession.id).label("session_count"),
            sqlfunc.sum(ListenerSession.duration_seconds).label("total_seconds"),
            sqlfunc.max(ListenerSession.started_at).label("last_seen"),
            sqlfunc.max(ListenerSession.country).label("country"),
            sqlfunc.max(ListenerSession.country_code).label("country_code"),
        )
        .join(ListenerSession, User.id == ListenerSession.user_id)
        .where(ListenerSession.ended_at.isnot(None))
        .group_by(User.id, User.email, User.full_name)
        .order_by(sqlfunc.max(ListenerSession.started_at).desc())
    )
    return [
        {
            "user_id": row.id,
            "email": row.email,
            "full_name": row.full_name,
            "session_count": row.session_count,
            "total_seconds": row.total_seconds or 0,
            "last_seen": row.last_seen,
            "country": row.country,
            "country_code": row.country_code,
        }
        for row in result.all()
    ]


@router.get("/listener-sessions", tags=["admin-listeners"])
async def get_listener_sessions(
    user_id: Optional[int] = Query(None),
    station: Optional[str] = Query(None),
    active_only: bool = Query(False),
    from_dt: Optional[datetime] = Query(None, alias="from"),
    to_dt: Optional[datetime] = Query(None, alias="to"),
    limit: int = Query(100, le=500),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List listener sessions with optional filters."""
    q = (
        select(ListenerSession, User.email, User.full_name)
        .join(User, ListenerSession.user_id == User.id)
        .order_by(ListenerSession.started_at.desc())
        .limit(limit)
    )
    if user_id:
        q = q.where(ListenerSession.user_id == user_id)
    if station:
        q = q.where(ListenerSession.station == station)
    if from_dt:
        q = q.where(ListenerSession.started_at >= from_dt)
    if to_dt:
        q = q.where(ListenerSession.started_at <= to_dt)
    if active_only:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=90)
        q = q.where(
            ListenerSession.ended_at.is_(None),
            ListenerSession.last_heartbeat_at >= cutoff,
        )

    result = await db.execute(q)
    rows = result.all()
    return [
        {
            **ListenerSessionRead.model_validate(session).model_dump(),
            "user_email": email,
            "user_name": full_name,
        }
        for session, email, full_name in rows
    ]
```

Add `from datetime import timedelta` to imports if not already present.

- [ ] **Step 2: Verify analytics endpoints work**

```bash
curl -s "http://localhost/api/v1/admin/listener-sessions/active" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

curl -s "http://localhost/api/v1/admin/listener-sessions/summary" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

curl -s "http://localhost/api/v1/admin/listener-sessions" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```
Expected: All return JSON arrays (empty or with data).

- [ ] **Step 3: Commit**

```bash
git add services/api/app/api/v1/endpoints/admin.py
git commit -m "feat: add listener analytics endpoints (active, summary, history)"
```

---

## Chunk 5: Infrastructure

### Task 16: Remove Icecast host port exposure

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Find and remove the Icecast port 8000 host mapping**

In `docker-compose.yml`, find the `icecast` service's `ports` section. It should look like:
```yaml
    ports:
      - "8000:8000"
```

Remove the `ports` section entirely from the `icecast` service (or change to internal-only — no host port). The Icecast container remains reachable from other containers on the Docker network as `icecast:8000`, but port 8000 is no longer bound to the host.

- [ ] **Step 2: Verify Icecast is no longer directly accessible but stream still works via Caddy**

```bash
docker compose up -d

# Should fail (direct access closed):
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/status.xsl
# Expected: connection refused

# Should work via Caddy (unauthenticated yet — stream auth comes in Task 17):
curl -s -o /dev/null -w "%{http_code}" http://localhost/stream/raido.mp3 &
sleep 2 && kill %1
# Expected: 200 (stream data)
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "security: remove Icecast host port 8000 — stream access via Caddy only"
```

---

### Task 17: Caddy forward_auth for stream

**Files:**
- Modify: `infra/Caddyfile`

- [ ] **Step 1: Update the main domain block (`raido.zorro.network, raido.zorro.home.local`)**

Find this block in the Caddyfile:
```caddy
	# Icecast stream
	handle_path /stream/* {
		reverse_proxy icecast:8000
	}
```

Replace with:
```caddy
	# Icecast stream — requires valid stream token
	handle_path /stream/* {
		forward_auth api:8000 {
			uri /api/v1/stream/validate
			copy_headers X-User-Id
		}
		reverse_proxy icecast:8000
	}
```

- [ ] **Step 2: Apply the same change to the `:80` block**

In the `:80` server block (starts at line ~143 in Caddyfile), find:
```caddy
	# Icecast stream
	handle_path /stream/* {
		reverse_proxy icecast:8000
	}
```
Replace with:
```caddy
	# Icecast stream — requires valid stream token
	handle_path /stream/* {
		forward_auth api:8000 {
			uri /api/v1/stream/validate
			copy_headers X-User-Id
		}
		reverse_proxy icecast:8000
	}
```

- [ ] **Step 3: Leave the Christmas block unchanged**

The `christmas.raido.zorro.network, :8888` block's `/stream/*` route stays as-is (intentionally open for internal use).

- [ ] **Step 4: Reload Caddy**

```bash
docker compose exec proxy caddy reload --config /etc/caddy/Caddyfile
```
Expected: `{"level":"info",...,"msg":"config loaded"}` or no errors.

- [ ] **Step 5: Verify the stream now requires a token**

```bash
# Without token — should be blocked:
curl -s -o /dev/null -w "%{http_code}" http://localhost/stream/raido.mp3
# Expected: 401 or 403

# With a valid stream token:
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"yourpassword"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

STREAM_TOKEN=$(curl -s http://localhost/api/v1/stream/token \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

curl -s -o /dev/null -w "%{http_code}" "http://localhost/stream/raido.mp3?token=$STREAM_TOKEN"
# Expected: 200 (stream data)
```

- [ ] **Step 6: Commit**

```bash
git add infra/Caddyfile
git commit -m "security: add Caddy forward_auth to gate Icecast stream with stream tokens"
```

---

## Chunk 6: Frontend Core

### Task 18: Route guard components

**Files:**
- Create: `web/src/components/RequireAuth.tsx`
- Create: `web/src/components/RequireAdmin.tsx`

- [ ] **Step 1: Create RequireAuth**

Create `web/src/components/RequireAuth.tsx`:
```tsx
import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

interface Props {
  children: React.ReactNode
}

export default function RequireAuth({ children }: Props) {
  const { token } = useAuthStore()
  const location = useLocation()

  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}
```

- [ ] **Step 2: Create RequireAdmin**

Create `web/src/components/RequireAdmin.tsx`:
```tsx
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

interface Props {
  children: React.ReactNode
}

export default function RequireAdmin({ children }: Props) {
  const { role } = useAuthStore()

  if (role !== 'admin') {
    return <Navigate to="/now-playing" replace />
  }

  return <>{children}</>
}
```

- [ ] **Step 3: Commit**

```bash
git add web/src/components/RequireAuth.tsx web/src/components/RequireAdmin.tsx
git commit -m "feat: add RequireAuth and RequireAdmin route guard components"
```

---

### Task 19: Register page + login page updates

**Files:**
- Create: `web/src/components/RegisterPage.tsx`
- Modify: `web/src/components/LoginPage.tsx`

- [ ] **Step 1: Create RegisterPage**

Create `web/src/components/RegisterPage.tsx`:
```tsx
import React, { useState } from 'react'
import { Link } from 'react-router-dom'

const API = '/api/v1'

export default function RegisterPage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${API}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, full_name: name }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Registration failed')
      setSubmitted(true)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (submitted) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="card p-8 w-full max-w-sm space-y-4 text-center">
          <div className="text-3xl">🎶</div>
          <h1 className="text-xl font-bold text-gray-100">You're on the list</h1>
          <p className="text-sm text-gray-400">
            Your account is pending approval. You'll be able to log in once an admin approves it.
          </p>
          <p className="text-xs text-gray-500">We log your approximate location for listener analytics.</p>
          <Link to="/login" className="block text-primary-400 hover:text-primary-300 text-sm">
            Back to sign in
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="card p-8 w-full max-w-sm space-y-6">
        <div>
          <h1 className="text-xl font-bold text-gray-100">Create account</h1>
          <p className="text-xs text-gray-500 mt-1">
            We log your approximate location for listener analytics.
          </p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              required
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:border-primary-500"
              placeholder="Your name"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:border-primary-500"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:border-primary-500"
              placeholder="••••••••"
            />
          </div>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white font-medium py-2 rounded-lg transition-colors"
          >
            {loading ? 'Please wait…' : 'Request access'}
          </button>
        </form>
        <p className="text-sm text-gray-500 text-center">
          Already have an account?{' '}
          <Link to="/login" className="text-primary-400 hover:text-primary-300">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Update LoginPage to use /auth/setup-status and handle pending**

In `web/src/components/LoginPage.tsx`, make these changes:

1. Change the `fetch` call from `/api/v1/auth/me` to `/api/v1/auth/setup-status`
2. After login success, change the redirect from `/raido/enrich` to `/now-playing` (listeners land here)
3. Update the after-login check: `if (isAuthenticated()) navigate('/now-playing'...)`
4. Handle the pending state in `handleSubmit`:

```tsx
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const endpoint = needsSetup ? `${API}/auth/setup` : `${API}/auth/login`
      const body: Record<string, string> = { email, password }
      if (needsSetup) body.full_name = name || 'Admin'

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()

      if (res.status === 403 && data.detail === 'account_pending') {
        setError('Your account is pending admin approval. Check back soon.')
        return
      }
      if (!res.ok) throw new Error(data.detail || 'Login failed')

      setAuth(data.access_token, data.user_id, data.email, data.role)
      navigate('/now-playing', { replace: true })
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }
```

5. Add a "Create account" link below the sign-in button:
```tsx
          <p className="text-sm text-gray-500 text-center">
            Don't have an account?{' '}
            <Link to="/register" className="text-primary-400 hover:text-primary-300">Request access</Link>
          </p>
```
(Add `import { Link } from 'react-router-dom'` to the imports.)

- [ ] **Step 3: Commit**

```bash
git add web/src/components/RegisterPage.tsx web/src/components/LoginPage.tsx
git commit -m "feat: add register page; update login for setup-status and pending state"
```

---

### Task 20: Role-based navigation in Layout

**Files:**
- Modify: `web/src/components/Layout.tsx`

- [ ] **Step 1: Read the current Layout.tsx to understand existing imports and nav structure**

```bash
cat web/src/components/Layout.tsx
```

Note: check what is already imported (icons, variables like `djAdminHref`, existing nav items). The nav array currently uses variables such as `djAdminHref` (a computed path based on the current station) and references icons like `SettingsIcon`, `RadioIcon`, etc. Keep all existing references intact.

- [ ] **Step 2: Update the navigation to be role-aware**

In `Layout.tsx`, update `useAuthStore` destructuring to include `role`:
```tsx
  const { isAuthenticated, clearAuth, role } = useAuthStore()
```

Add a computed flag and make the nav conditional — append the admin items to whatever nav array already exists:
```tsx
  const isAdmin = role === 'admin'

  // Keep all existing nav items, append admin-only items when role === 'admin'
  // Replace the existing static nav array with this pattern:
  const adminNav = isAdmin ? [
    // djAdminHref and all icon references must match what is already imported
    // in this file — do not add new imports for things already imported
    { name: 'Users', href: '/admin/users', icon: UsersIcon },       // use UsersIcon if imported, else HomeIcon
    { name: 'Listeners', href: '/admin/listeners', icon: ActivityIcon }, // use ActivityIcon if imported, else WifiIcon
  ] : []
  // Spread adminNav at the end of the existing navigation array
```

> **Important:** Only reference icons that are already imported in `Layout.tsx`. If `UsersIcon` or `ActivityIcon` are not imported, use any icon that is already present as a placeholder (e.g., `HomeIcon`).

- [ ] **Step 2: Fix the stream link in the header**

The header currently has:
```tsx
              <a href="/stream/raido.mp3" ...>
```

This needs the stream token. Change it to a button that handles token fetch internally, or simply remove the direct stream link from the header and let the RadioPlayer handle it. For now, hide the direct stream link from the header (it's better handled in the player component):

Replace the `<a href="/stream/raido.mp3"...>` block with just the connection status indicator (no link):
```tsx
              <div
                className={`flex items-center gap-1.5 text-xs font-medium ${
                  isConnected ? 'text-green-400' : 'text-red-400'
                }`}
                role="status"
              >
                {isConnected ? <WifiIcon className="h-4 w-4" /> : <WifiOffIcon className="h-4 w-4" />}
                <span className="hidden sm:inline">{isConnected ? 'Live' : 'Offline'}</span>
              </div>
```

- [ ] **Step 3: Rebuild frontend and verify nav changes**

```bash
docker compose build web && docker compose up -d web
```
Log in as admin → should see all nav items. (Listener view will be tested after the guard changes in App.tsx.)

- [ ] **Step 4: Commit**

```bash
git add web/src/components/Layout.tsx
git commit -m "feat: role-based navigation — admin sees all, listener sees subset"
```

---

### Task 21: Wire up App.tsx with route guards + new routes

**Files:**
- Modify: `web/src/App.tsx`

- [ ] **Step 1: Update App.tsx**

Replace the contents of `web/src/App.tsx` with:
```tsx
import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'

import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import RequireAuth from './components/RequireAuth'
import RequireAdmin from './components/RequireAdmin'

import NowPlaying from './components/NowPlaying'
import CommentaryTranscript from './components/CommentaryTranscript'
import ComingUp from './components/ComingUp'
import PlayHistory from './components/PlayHistory'
import TTSMonitor from './components/TTSMonitor'
import Analytics from './components/Analytics'
import StationControlPanel from './components/StationControlPanel'
import MediaLibrary from './components/MediaLibrary'
import LoginPage from './components/LoginPage'
import RegisterPage from './components/RegisterPage'
import MBEnrich from './components/MBEnrich'
import CommentaryBrowser from './components/CommentaryBrowser'
import UserManagement from './components/admin/UserManagement'
import ListenerSessions from './components/admin/ListenerSessions'

function App() {
  return (
    <div className="min-h-screen">
      <Layout>
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<Navigate to="/now-playing" replace />} />

            {/* Public routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Listener routes (any authenticated user) */}
            <Route path="/now-playing" element={
              <RequireAuth>
                <div className="space-y-6">
                  <ErrorBoundary fallback={<div className="card p-6 text-gray-300">Failed to render Now Playing.</div>}>
                    <NowPlaying />
                  </ErrorBoundary>
                  <CommentaryTranscript />
                  <ErrorBoundary fallback={<div className="card p-6 text-gray-300">Failed to render Coming Up.</div>}>
                    <ComingUp />
                  </ErrorBoundary>
                  <ErrorBoundary fallback={<div className="card p-6 text-gray-300">Failed to render Play History.</div>}>
                    <PlayHistory />
                  </ErrorBoundary>
                </div>
              </RequireAuth>
            } />

            <Route path="/history" element={<RequireAuth><PlayHistory /></RequireAuth>} />
            <Route path="/transcripts" element={<RequireAuth><CommentaryBrowser /></RequireAuth>} />

            {/* Admin-only routes */}
            <Route path="/analytics" element={<RequireAuth><RequireAdmin><Analytics /></RequireAdmin></RequireAuth>} />
            <Route path="/tts" element={<Navigate to="/raido/admin" replace />} />
            <Route path="/raido/admin" element={<RequireAuth><RequireAdmin><TTSMonitor /></RequireAdmin></RequireAuth>} />
            <Route path="/:station/admin" element={<RequireAuth><RequireAdmin><TTSMonitor /></RequireAdmin></RequireAuth>} />
            <Route path="/stations" element={<RequireAuth><RequireAdmin><StationControlPanel /></RequireAdmin></RequireAuth>} />
            <Route path="/media" element={<RequireAuth><RequireAdmin><MediaLibrary /></RequireAdmin></RequireAuth>} />
            <Route path="/media/tracks/:trackId" element={<RequireAuth><RequireAdmin><MediaLibrary /></RequireAdmin></RequireAuth>} />
            <Route path="/raido/enrich" element={<RequireAuth><RequireAdmin><MBEnrich /></RequireAdmin></RequireAuth>} />
            <Route path="/admin/users" element={<RequireAuth><RequireAdmin><UserManagement /></RequireAdmin></RequireAuth>} />
            <Route path="/admin/listeners" element={<RequireAuth><RequireAdmin><ListenerSessions /></RequireAdmin></RequireAuth>} />

            <Route path="*" element={
              <div className="card p-12 flex flex-col items-center gap-2 text-center">
                <p className="text-4xl font-bold text-gray-700">404</p>
                <p className="text-gray-400 font-medium mt-1">Page not found</p>
              </div>
            } />
          </Routes>
        </ErrorBoundary>
      </Layout>
    </div>
  )
}

export default App
```

- [ ] **Step 2: Build and verify routing**

```bash
docker compose build web && docker compose up -d web
```

- Unauthenticated → visit `/now-playing` → redirected to `/login` ✓
- Log in as listener → visit `/stations` → redirected to `/now-playing` ✓
- Log in as admin → visit `/stations` → page loads ✓
- Visit `/register` → registration form loads ✓

- [ ] **Step 3: Commit**

```bash
git add web/src/App.tsx
git commit -m "feat: add route guards to all routes; wire admin pages and register route"
```

---

### Task 22: RadioPlayer stream token + session tracking

**Files:**
- Modify: `web/src/components/RadioPlayer.tsx`

Read the current RadioPlayer first, then make these changes:

- [ ] **Step 1: Read RadioPlayer to understand current implementation**

```bash
cat web/src/components/RadioPlayer.tsx
```

- [ ] **Step 2: Add stream token fetching and session tracking**

The RadioPlayer needs to:
1. Fetch a stream token before setting the audio `src`
2. Silently refresh the token every 10 minutes
3. Start a listener session when audio begins playing
4. Send a heartbeat every 30 seconds while playing
5. End the session on pause, component unmount, or page unload

Add a utility module `web/src/utils/listenerSession.ts`:
```ts
const API = '/api/v1'

function authHeaders() {
  const auth = JSON.parse(localStorage.getItem('raido-auth') || '{}')
  const token = auth?.state?.token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function fetchStreamToken(): Promise<string | null> {
  try {
    const res = await fetch(`${API}/stream/token`, { headers: authHeaders() })
    if (!res.ok) return null
    const data = await res.json()
    return data.token as string
  } catch {
    return null
  }
}

export async function startSession(station: string): Promise<number | null> {
  try {
    const res = await fetch(`${API}/listeners/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ station }),
    })
    if (!res.ok) return null
    const data = await res.json()
    return data.session_id as number
  } catch {
    return null
  }
}

export async function sendHeartbeat(sessionId: number): Promise<boolean> {
  try {
    const res = await fetch(`${API}/listeners/sessions/${sessionId}/heartbeat`, {
      method: 'POST',
      headers: authHeaders(),
    })
    return res.ok
  } catch {
    return false
  }
}

export async function endSession(sessionId: number): Promise<void> {
  try {
    await fetch(`${API}/listeners/sessions/${sessionId}/end`, {
      method: 'POST',
      headers: authHeaders(),
    })
  } catch {}
}
```

- [ ] **Step 3: Integrate into RadioPlayer**

In the RadioPlayer component, add the following behavior using `useRef` and `useEffect`:

```tsx
import { fetchStreamToken, startSession, sendHeartbeat, endSession } from '../utils/listenerSession'
import { useAuthStore } from '../store/authStore'

// Inside the component:
const { token: authToken } = useAuthStore()
// Inside the component:
const audioRef = useRef<HTMLAudioElement>(null)
const sessionIdRef = useRef<number | null>(null)
const heartbeatIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
const tokenRefreshIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

async function loadStreamWithToken(station: string) {
  const streamToken = await fetchStreamToken()
  if (!streamToken || !audioRef.current) return
  const src = `/stream/${station}.mp3?token=${streamToken}`
  const wasPlaying = !audioRef.current.paused
  audioRef.current.src = src
  if (wasPlaying) audioRef.current.play().catch(() => {})
}

async function handlePlay(station: string) {
  // Start session if none active
  if (!sessionIdRef.current) {
    sessionIdRef.current = await startSession(station)
  }
  // Heartbeat every 30s
  if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current)
  heartbeatIntervalRef.current = setInterval(async () => {
    if (sessionIdRef.current) {
      const ok = await sendHeartbeat(sessionIdRef.current)
      if (!ok) {
        // Heartbeat failed (session stale-closed or network issue) — start a new one
        sessionIdRef.current = await startSession(station)
      }
    }
  }, 30_000)
}

async function handlePause() {
  if (heartbeatIntervalRef.current) {
    clearInterval(heartbeatIntervalRef.current)
    heartbeatIntervalRef.current = null
  }
  if (sessionIdRef.current) {
    await endSession(sessionIdRef.current)
    sessionIdRef.current = null
  }
}

useEffect(() => {
  if (!authToken) return
  // Initial stream token load
  loadStreamWithToken(selectedStation)
  // Refresh stream token every 10 minutes
  tokenRefreshIntervalRef.current = setInterval(() => {
    loadStreamWithToken(selectedStation)
  }, 10 * 60 * 1000)

  return () => {
    if (tokenRefreshIntervalRef.current) clearInterval(tokenRefreshIntervalRef.current)
    if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current)
    if (sessionIdRef.current) endSession(sessionIdRef.current)
  }
}, [authToken, selectedStation])

// Bind play/pause events to the audio element:
useEffect(() => {
  const audio = audioRef.current
  if (!audio) return
  const onPlay = () => handlePlay(selectedStation)
  const onPause = () => handlePause()
  audio.addEventListener('play', onPlay)
  audio.addEventListener('pause', onPause)
  return () => {
    audio.removeEventListener('play', onPlay)
    audio.removeEventListener('pause', onPause)
  }
}, [selectedStation])
```

> **Note:** If RadioPlayer doesn't use an `<audio>` element directly (it may use a browser audio API or embed an Icecast stream URL in an `<audio>` tag), adapt accordingly. The key integration points are: token in audio src, session start on play, heartbeat interval while playing, session end on pause/unmount.

- [ ] **Step 4: Build and test end-to-end**

```bash
docker compose build web && docker compose up -d web
```

1. Log in as admin
2. Open the player, press play
3. Check the DB: `SELECT * FROM listener_sessions ORDER BY started_at DESC LIMIT 5;`
4. Wait 35 seconds → check `last_heartbeat_at` updated
5. Press pause → check `ended_at` is set

- [ ] **Step 5: Commit**

```bash
git add web/src/utils/listenerSession.ts web/src/components/RadioPlayer.tsx
git commit -m "feat: RadioPlayer fetches stream token and tracks listener sessions"
```

---

## Chunk 7: Frontend Admin Pages

### Task 23: UserManagement admin page

**Files:**
- Create: `web/src/components/admin/UserManagement.tsx`

- [ ] **Step 1: Create the admin directory and UserManagement component**

```bash
mkdir -p web/src/components/admin
```

Create `web/src/components/admin/UserManagement.tsx`:
```tsx
import React, { useEffect, useState } from 'react'
import { useAuthStore } from '../../store/authStore'

const API = '/api/v1'

interface AdminUser {
  id: number
  email: string
  full_name: string | null
  role: string
  is_active: boolean
  is_verified: boolean
  last_login_at: string | null
  created_at: string
}

function authHeaders(token: string | null) {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function CreateUserForm({ token, onCreated, onCancel }: { token: string | null, onCreated: () => void, onCancel: () => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [role, setRole] = useState('listener')
  const [err, setErr] = useState('')

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setErr('')
    const res = await fetch(`${API}/admin/users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
      body: JSON.stringify({ email, password, full_name: name, role }),
    })
    const data = await res.json()
    if (!res.ok) { setErr(data.detail || 'Error'); return }
    onCreated()
    onCancel()
  }

  return (
    <form onSubmit={submit} className="bg-gray-800 rounded-lg p-4 space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <input className="bg-gray-700 rounded px-3 py-2 text-gray-100 text-sm" placeholder="Name" value={name} onChange={e => setName(e.target.value)} />
        <input className="bg-gray-700 rounded px-3 py-2 text-gray-100 text-sm" placeholder="Email" type="email" required value={email} onChange={e => setEmail(e.target.value)} />
        <input className="bg-gray-700 rounded px-3 py-2 text-gray-100 text-sm" placeholder="Password" type="password" required value={password} onChange={e => setPassword(e.target.value)} />
        <select className="bg-gray-700 rounded px-3 py-2 text-gray-100 text-sm" value={role} onChange={e => setRole(e.target.value)}>
          <option value="listener">listener</option>
          <option value="admin">admin</option>
        </select>
      </div>
      {err && <p className="text-red-400 text-xs">{err}</p>}
      <div className="flex gap-2">
        <button type="submit" className="bg-primary-600 hover:bg-primary-500 text-white text-sm px-3 py-1 rounded-lg">Create</button>
        <button type="button" onClick={onCancel} className="text-gray-400 hover:text-gray-300 text-sm px-3 py-1">Cancel</button>
      </div>
    </form>
  )
}

export default function UserManagement() {
  const { token } = useAuthStore()
  const [pending, setPending] = useState<AdminUser[]>([])
  const [all, setAll] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showCreate, setShowCreate] = useState(false)

  async function loadUsers() {
    setLoading(true)
    try {
      const [pendingRes, allRes] = await Promise.all([
        fetch(`${API}/admin/users?status=pending`, { headers: authHeaders(token) }),
        fetch(`${API}/admin/users`, { headers: authHeaders(token) }),
      ])
      setPending(await pendingRes.json())
      setAll(await allRes.json())
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadUsers() }, [])

  async function approve(id: number) {
    await fetch(`${API}/admin/users/${id}/approve`, {
      method: 'POST',
      headers: authHeaders(token),
    })
    loadUsers()
  }

  async function suspend(id: number) {
    await fetch(`${API}/admin/users/${id}/suspend`, {
      method: 'POST',
      headers: authHeaders(token),
    })
    loadUsers()
  }

  async function deleteUser(id: number) {
    if (!confirm('Delete this user?')) return
    await fetch(`${API}/admin/users/${id}`, {
      method: 'DELETE',
      headers: authHeaders(token),
    })
    loadUsers()
  }

  function statusBadge(u: AdminUser) {
    if (u.is_active) return <span className="text-green-400 text-xs">active</span>
    if (!u.is_verified) return <span className="text-yellow-400 text-xs">pending</span>
    return <span className="text-red-400 text-xs">suspended</span>
  }

  if (loading) return <div className="text-gray-400 p-4">Loading users…</div>
  if (error) return <div className="text-red-400 p-4">{error}</div>

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-100">User Management</h1>

      {pending.length > 0 && (
        <section className="card p-6 space-y-4">
          <h2 className="text-lg font-semibold text-yellow-400">Pending Approval ({pending.length})</h2>
          <div className="space-y-3">
            {pending.map(u => (
              <div key={u.id} className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-3">
                <div>
                  <p className="text-gray-100 font-medium">{u.full_name || '(no name)'}</p>
                  <p className="text-gray-400 text-sm">{u.email}</p>
                  <p className="text-gray-500 text-xs">Registered {new Date(u.created_at).toLocaleDateString()}</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => approve(u.id)}
                    className="bg-green-600 hover:bg-green-500 text-white text-sm px-3 py-1 rounded-lg"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => deleteUser(u.id)}
                    className="bg-red-700 hover:bg-red-600 text-white text-sm px-3 py-1 rounded-lg"
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-100">All Users</h2>
          <button
            onClick={() => setShowCreate(v => !v)}
            className="bg-primary-600 hover:bg-primary-500 text-white text-sm px-3 py-1 rounded-lg"
          >
            + Create user
          </button>
        </div>
        {showCreate && (
          <CreateUserForm token={token} onCreated={loadUsers} onCancel={() => setShowCreate(false)} />
        )}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-700">
                <th className="pb-2 pr-4">Name</th>
                <th className="pb-2 pr-4">Email</th>
                <th className="pb-2 pr-4">Role</th>
                <th className="pb-2 pr-4">Status</th>
                <th className="pb-2 pr-4">Last login</th>
                <th className="pb-2">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {all.map(u => (
                <tr key={u.id} className="text-gray-300">
                  <td className="py-2 pr-4">{u.full_name || '—'}</td>
                  <td className="py-2 pr-4">{u.email}</td>
                  <td className="py-2 pr-4 text-gray-400">{u.role}</td>
                  <td className="py-2 pr-4">{statusBadge(u)}</td>
                  <td className="py-2 pr-4 text-gray-500 text-xs">
                    {u.last_login_at ? new Date(u.last_login_at).toLocaleDateString() : 'Never'}
                  </td>
                  <td className="py-2">
                    <div className="flex gap-2">
                      {!u.is_active && u.is_verified && (
                        <button onClick={() => approve(u.id)} className="text-green-400 hover:text-green-300 text-xs">Activate</button>
                      )}
                      {u.is_active && u.role !== 'admin' && (
                        <button onClick={() => suspend(u.id)} className="text-yellow-400 hover:text-yellow-300 text-xs">Suspend</button>
                      )}
                      <button onClick={() => deleteUser(u.id)} className="text-red-400 hover:text-red-300 text-xs">Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
```

- [ ] **Step 2: Build and verify**

```bash
docker compose build web && docker compose up -d web
# Navigate to /admin/users as admin
```
Expected: Pending users shown in yellow section, full user table below.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/admin/UserManagement.tsx
git commit -m "feat: add UserManagement admin page with pending approval queue"
```

---

### Task 24: ListenerSessions admin page

**Files:**
- Create: `web/src/components/admin/ListenerSessions.tsx`

- [ ] **Step 1: Create ListenerSessions component**

Create `web/src/components/admin/ListenerSessions.tsx`:
```tsx
import React, { useEffect, useState } from 'react'
import { useAuthStore } from '../../store/authStore'

const API = '/api/v1'

interface SessionHistory {
  id: number
  user_email: string
  user_name: string | null
  station: string
  started_at: string
  ended_at: string | null
  duration_seconds: number | null
  city: string | null
  country: string | null
  browser: string | null
  device_type: string | null
}

interface ActiveSession {
  id: number
  user_email: string
  user_name: string | null
  station: string
  city: string | null
  country: string | null
  country_code: string | null
  browser: string | null
  os: string | null
  device_type: string | null
  current_duration_seconds: number
}

interface SessionSummary {
  user_id: number
  email: string
  full_name: string | null
  session_count: number
  total_seconds: number
  last_seen: string | null
  country: string | null
  country_code: string | null
}

function fmtDuration(secs: number) {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

function authHeaders(token: string | null) {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export default function ListenerSessions() {
  const { token } = useAuthStore()
  const [active, setActive] = useState<ActiveSession[]>([])
  const [summary, setSummary] = useState<SessionSummary[]>([])
  const [history, setHistory] = useState<SessionHistory[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function load() {
    setLoading(true)
    try {
      const [activeRes, summaryRes, historyRes] = await Promise.all([
        fetch(`${API}/admin/listener-sessions/active`, { headers: authHeaders(token) }),
        fetch(`${API}/admin/listener-sessions/summary`, { headers: authHeaders(token) }),
        fetch(`${API}/admin/listener-sessions?limit=100`, { headers: authHeaders(token) }),
      ])
      setActive(await activeRes.json())
      setSummary(await summaryRes.json())
      setHistory(await historyRes.json())
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, 30_000)  // refresh every 30s
    return () => clearInterval(interval)
  }, [])

  if (loading && active.length === 0) return <div className="text-gray-400 p-4">Loading…</div>
  if (error) return <div className="text-red-400 p-4">{error}</div>

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-100">Listener Analytics</h1>

      {/* Active Now */}
      <section className="card p-6 space-y-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold text-gray-100">Listening Now</h2>
          <span className="live-dot" aria-hidden />
          <span className="text-gray-400 text-sm">{active.length} active</span>
        </div>
        {active.length === 0 ? (
          <p className="text-gray-500 text-sm">No one is listening right now.</p>
        ) : (
          <div className="space-y-2">
            {active.map(s => (
              <div key={s.id} className="bg-gray-800 rounded-lg px-4 py-3 flex items-center justify-between">
                <div>
                  <p className="text-gray-100 font-medium">{s.user_name || s.user_email}</p>
                  <p className="text-gray-400 text-xs">
                    {s.station} · {s.city && s.country ? `${s.city}, ${s.country}` : s.country || 'Unknown location'} · {s.browser} on {s.device_type}
                  </p>
                </div>
                <span className="text-green-400 text-sm font-mono">{fmtDuration(s.current_duration_seconds)}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Per-user summary */}
      <section className="card p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-100">Listener Summary</h2>
        {summary.length === 0 ? (
          <p className="text-gray-500 text-sm">No completed sessions yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-700">
                  <th className="pb-2 pr-4">User</th>
                  <th className="pb-2 pr-4">Sessions</th>
                  <th className="pb-2 pr-4">Total time</th>
                  <th className="pb-2 pr-4">Location</th>
                  <th className="pb-2">Last seen</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {summary.map(u => (
                  <tr key={u.user_id} className="text-gray-300">
                    <td className="py-2 pr-4">
                      <p>{u.full_name || u.email}</p>
                      {u.full_name && <p className="text-gray-500 text-xs">{u.email}</p>}
                    </td>
                    <td className="py-2 pr-4">{u.session_count}</td>
                    <td className="py-2 pr-4 font-mono">{fmtDuration(u.total_seconds)}</td>
                    <td className="py-2 pr-4">{u.country || '—'}</td>
                    <td className="py-2 text-gray-500 text-xs">
                      {u.last_seen ? new Date(u.last_seen).toLocaleDateString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Session history */}
      <section className="card p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-100">Session History</h2>
        {history.length === 0 ? (
          <p className="text-gray-500 text-sm">No sessions yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-700">
                  <th className="pb-2 pr-4">User</th>
                  <th className="pb-2 pr-4">Station</th>
                  <th className="pb-2 pr-4">Duration</th>
                  <th className="pb-2 pr-4">Location</th>
                  <th className="pb-2 pr-4">Device</th>
                  <th className="pb-2">When</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {history.map(s => (
                  <tr key={s.id} className="text-gray-300">
                    <td className="py-2 pr-4">{s.user_name || s.user_email}</td>
                    <td className="py-2 pr-4">{s.station}</td>
                    <td className="py-2 pr-4 font-mono">{s.duration_seconds != null ? fmtDuration(s.duration_seconds) : s.ended_at ? '—' : <span className="text-green-400">live</span>}</td>
                    <td className="py-2 pr-4">{s.city && s.country ? `${s.city}, ${s.country}` : s.country || '—'}</td>
                    <td className="py-2 pr-4 text-gray-500 text-xs">{s.browser} · {s.device_type}</td>
                    <td className="py-2 text-gray-500 text-xs">{new Date(s.started_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
```

- [ ] **Step 2: Build and verify**

```bash
docker compose build web && docker compose up -d web
# Navigate to /admin/listeners as admin
```
Expected: "Active Now" section (auto-refreshes every 30s), Listener Summary table, Session History table below.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/admin/ListenerSessions.tsx
git commit -m "feat: add ListenerSessions admin page with active and summary views"
```

---

## Final Integration Verification

- [ ] **End-to-end flow test:**

1. Open `/register` → fill form → submit → see pending message
2. Log in as admin → go to `/admin/users` → see pending user → click Approve
3. Log out, log in as the new listener account → land on `/now-playing`
4. Try to navigate to `/stations` → redirected to `/now-playing` ✓
5. Press play on the player → check DB: `SELECT * FROM listener_sessions ORDER BY id DESC LIMIT 1;`
6. Wait 35s → check `last_heartbeat_at` has updated
7. Pause → check `ended_at` is set, `duration_seconds` is populated
8. As admin, go to `/admin/listeners` → see listener summary ✓

- [ ] **Push and deploy:**

```bash
git push origin feature/listener-role

# Deploy to PCT 127:
pct exec 127 -- bash -c "cd /opt/raido && git pull raido main"
pct exec 127 -- bash -c "cd /opt/raido && docker compose build api web"
pct exec 127 -- bash -c "cd /opt/raido && docker compose up -d"
```

> **Note:** The deployment pull is from `main`. Merge `feature/listener-role` to `main` first, or adjust the pull command to pull from the feature branch for testing.

- [ ] **Add STREAM_TOKEN_SECRET to production .env on PCT 127:**

```bash
pct exec 127 -- bash -c "echo 'STREAM_TOKEN_SECRET=<generate-with-openssl-rand-hex-32>' >> /opt/raido/.env"
```

Generate a strong secret:
```bash
openssl rand -hex 32
```

- [ ] **Volume-mount GeoIP database (optional — skip if not yet downloaded):**

Download GeoLite2-City.mmdb from MaxMind (free account required), copy to PCT 127, and mount it into the API container by adding to `docker-compose.yml`:
```yaml
    volumes:
      - /opt/raido/geoip:/app/geoip:ro
```
Then restart: `docker compose up -d api`.
