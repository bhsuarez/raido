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
