import asyncio
import json
import time
from typing import Any, Dict, Optional, Sequence

import httpx
import structlog
from fastapi import Depends, HTTPException, WebSocket, WebSocketException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.schemas.auth import AuthenticatedUser

logger = structlog.get_logger()

# HTTP bearer scheme for FastAPI dependencies
bearer_scheme = HTTPBearer(auto_error=False)

# In-memory caches for OIDC discovery and JWKS responses
_openid_config: Optional[Dict[str, Any]] = None
_openid_config_expires_at: float = 0.0
_openid_lock = asyncio.Lock()

_jwks_data: Optional[Dict[str, Any]] = None
_jwks_expires_at: float = 0.0
_jwks_lock = asyncio.Lock()

_CACHE_TTL_SECONDS = 60 * 10  # 10 minutes


def _clean_base_url(url: str) -> str:
    """Ensure URLs don't end with a trailing slash."""

    return url.rstrip("/")


async def _fetch_json(url: str) -> Dict[str, Any]:
    """Fetch JSON content from the provided URL with basic error handling."""

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def _get_openid_configuration() -> Dict[str, Any]:
    """Retrieve and cache the OpenID Connect discovery document."""

    global _openid_config, _openid_config_expires_at

    if _openid_config and time.time() < _openid_config_expires_at:
        return _openid_config

    if not settings.AUTHENTIK_ISSUER:
        raise RuntimeError("AUTHENTIK_ISSUER is not configured")

    async with _openid_lock:
        if _openid_config and time.time() < _openid_config_expires_at:
            return _openid_config

        issuer = _clean_base_url(settings.AUTHENTIK_ISSUER)
        discovery_url = f"{issuer}/.well-known/openid-configuration"

        try:
            logger.debug("Fetching OpenID configuration", url=discovery_url)
            _openid_config = await _fetch_json(discovery_url)
            _openid_config_expires_at = time.time() + _CACHE_TTL_SECONDS
        except httpx.HTTPError as exc:
            logger.error("Failed to load OpenID configuration", url=discovery_url, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication provider is unavailable",
            ) from exc

    return _openid_config or {}


async def _get_jwks() -> Dict[str, Any]:
    """Retrieve and cache JWKS signing keys."""

    global _jwks_data, _jwks_expires_at

    if _jwks_data and time.time() < _jwks_expires_at:
        return _jwks_data

    async with _jwks_lock:
        if _jwks_data and time.time() < _jwks_expires_at:
            return _jwks_data

        jwks_uri = settings.AUTHENTIK_JWKS_URL
        if not jwks_uri:
            config = await _get_openid_configuration()
            jwks_uri = config.get("jwks_uri")
            if not jwks_uri:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication provider JWKS endpoint is not configured",
                )

        try:
            logger.debug("Fetching JWKS", url=jwks_uri)
            _jwks_data = await _fetch_json(jwks_uri)
            _jwks_expires_at = time.time() + _CACHE_TTL_SECONDS
        except httpx.HTTPError as exc:
            logger.error("Failed to load JWKS", url=jwks_uri, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to retrieve authentication signing keys",
            ) from exc

    return _jwks_data or {}


def _normalise_groups(groups: Any) -> Sequence[str]:
    if groups is None:
        return []
    if isinstance(groups, str):
        return [groups]
    if isinstance(groups, (list, tuple, set)):
        return [str(item) for item in groups]
    return []


def _parse_scopes(scope_value: Any) -> Sequence[str]:
    if isinstance(scope_value, str):
        return [scope for scope in scope_value.split() if scope]
    if isinstance(scope_value, (list, tuple, set)):
        return [str(item) for item in scope_value]
    return []


def _build_authenticated_user(claims: Dict[str, Any]) -> AuthenticatedUser:
    groups = _normalise_groups(claims.get("groups") or claims.get("roles"))
    scopes = set(_parse_scopes(claims.get("scope")))
    permissions = set(_parse_scopes(claims.get("permissions")))

    display_name = (
        claims.get("name")
        or claims.get("preferred_username")
        or claims.get("nickname")
        or claims.get("email")
    )

    return AuthenticatedUser(
        sub=claims.get("sub"),
        email=claims.get("email"),
        preferred_username=claims.get("preferred_username"),
        display_name=display_name,
        groups=list(groups),
        scopes=scopes,
        permissions=permissions,
        raw_claims=claims,
        is_authenticated=True,
    )


async def _decode_token(token: str) -> Dict[str, Any]:
    jwks = await _get_jwks()
    if "keys" not in jwks:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication signing keys are unavailable",
        )

    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        logger.warning("Invalid JWT header", error=str(exc))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    kid = unverified_header.get("kid")
    alg = unverified_header.get("alg", "RS256")

    matching_key = None
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            matching_key = key
            break

    if not matching_key:
        logger.warning("Unable to match JWKS key for token", kid=kid)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signing key")

    issuer = _clean_base_url(settings.AUTHENTIK_ISSUER or "")
    audience = settings.AUTHENTIK_AUDIENCE or settings.AUTHENTIK_CLIENT_ID

    decode_kwargs: Dict[str, Any] = {
        "algorithms": [alg],
        "issuer": issuer or None,
        "options": {"verify_aud": bool(audience)},
        "leeway": 10,
    }

    if audience:
        decode_kwargs["audience"] = audience

    try:
        claims = jwt.decode(token, matching_key, **decode_kwargs)
        logger.debug("Successfully validated access token", subject=claims.get("sub"))
        return claims
    except JWTError as exc:
        logger.warning("Failed to validate JWT", error=str(exc))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token validation failed") from exc


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> AuthenticatedUser:
    """Resolve the authenticated user for standard HTTP requests."""

    if not settings.AUTHENTIK_ENABLED:
        # Authentication disabled – return an unauthenticated placeholder user
        return AuthenticatedUser()

    if not settings.AUTHENTIK_ISSUER:
        logger.error("Authentik issuer not configured while authentication enabled")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured correctly",
        )

    if credentials is None or not credentials.scheme.lower() == "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    claims = await _decode_token(token)
    return _build_authenticated_user(claims)


async def require_authenticated_user(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Ensure a request is made by an authenticated user when Authentik is enabled."""

    if not settings.AUTHENTIK_ENABLED:
        return user

    if not user.is_authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    return user


def _admin_groups() -> Sequence[str]:
    groups_raw = settings.AUTHENTIK_ADMIN_GROUPS or ""
    return [group.strip() for group in groups_raw.split(",") if group.strip()]


async def require_admin_user(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    """Ensure the requester belongs to one of the configured administrator groups."""

    if not settings.AUTHENTIK_ENABLED:
        return user

    admin_groups = _admin_groups()
    if not user.is_authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    if admin_groups and not user.has_group(*admin_groups):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")

    return user


async def authenticate_websocket(websocket: WebSocket) -> AuthenticatedUser:
    """Validate WebSocket connections using the same access token checks."""

    if not settings.AUTHENTIK_ENABLED:
        return AuthenticatedUser()

    if not settings.AUTHENTIK_ISSUER:
        raise WebSocketException(
            code=status.WS_1011_INTERNAL_ERROR,
            reason="Authentication is not configured correctly",
        )

    token = websocket.query_params.get("token")
    if not token:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Missing access token",
        )

    try:
        claims = await _decode_token(token)
    except HTTPException as exc:  # noqa: B902 - re-map to WebSocket exception
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=str(exc.detail),
        ) from exc

    user = _build_authenticated_user(claims)
    websocket.scope["auth_user"] = json.loads(user.model_dump_json())
    return user
