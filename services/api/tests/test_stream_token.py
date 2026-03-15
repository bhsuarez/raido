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
