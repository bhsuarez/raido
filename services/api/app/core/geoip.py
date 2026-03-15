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
