"""Shared slowapi rate limiter instance.

Import this module everywhere rate limiting decorators or middleware are needed.
Creating multiple Limiter instances causes the exception handler to mismatch.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
