"""Tests for the Open-Meteo weather client used by the home page."""
from unittest.mock import MagicMock, patch

import diskcache
import pytest
import requests

from app import cache as cache_module
from app import weather


def _payload(code=2, is_day=1, temp=71.6):
    """Build an Open-Meteo-shaped reply with the given weather code, day flag, and current temperature."""
    return {
        "current": {"temperature_2m": temp, "weather_code": code, "is_day": is_day},
        "daily": {"temperature_2m_max": [78.4], "temperature_2m_min": [54.9]},
    }


def _response(payload=None, status_error=None):
    """Build a fake requests.Response whose json() returns payload; raise_for_status() raises status_error if given."""
    resp = MagicMock()
    resp.json.return_value = payload
    if status_error:
        resp.raise_for_status.side_effect = status_error
    return resp


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path):
    """Give each test an empty disk cache so cached weather never leaks between tests."""
    cache = diskcache.Cache(str(tmp_path / "cache"))
    with patch.object(cache_module, "_cache", cache):
        yield cache
    cache.close()


def test_fetch_weather_normalizes_open_meteo_reply():
    with patch.object(weather.http_requests, "get", return_value=_response(_payload())):
        result = weather.fetch_weather()
    assert result == {
        "temp": 72,
        "high": 78,
        "low": 55,
        "condition": "Partly cloudy",
        "icon": "partly",
        "location": weather.WEATHER_LOCATION,
    }


def test_fetch_weather_requests_configured_location_in_fahrenheit():
    with patch.object(weather.http_requests, "get", return_value=_response(_payload())) as mock_get:
        weather.fetch_weather()
    params = mock_get.call_args.kwargs["params"]
    assert mock_get.call_args.args[0] == weather.OPEN_METEO_URL
    assert params["latitude"] == weather.WEATHER_LAT
    assert params["longitude"] == weather.WEATHER_LON
    assert params["temperature_unit"] == "fahrenheit"
    assert mock_get.call_args.kwargs["timeout"] <= 5


@pytest.mark.parametrize("code, is_day, condition, icon", [
    (0, 1, "Clear", "clear"),
    (0, 0, "Clear", "night"),
    (2, 0, "Partly cloudy", "partly"),
    (45, 1, "Fog", "fog"),
    (63, 1, "Rain", "rain"),
    (75, 1, "Heavy snow", "snow"),
    (95, 1, "Thunderstorm", "storm"),
    (42, 1, "Unknown", "cloudy"),
])
def test_weather_code_maps_to_condition_and_icon(code, is_day, condition, icon):
    with patch.object(weather.http_requests, "get", return_value=_response(_payload(code, is_day))):
        result = weather.fetch_weather()
    assert (result["condition"], result["icon"]) == (condition, icon)


def test_network_error_returns_none():
    with patch.object(weather.http_requests, "get", side_effect=requests.ConnectionError("down")):
        assert weather.fetch_weather() is None


def test_http_error_returns_none():
    resp = _response(status_error=requests.HTTPError("400 Bad Request"))
    with patch.object(weather.http_requests, "get", return_value=resp):
        assert weather.fetch_weather() is None


@pytest.mark.parametrize("payload", [
    {"current": {"temperature_2m": 70, "weather_code": 0, "is_day": 1}},  # no daily block
    _payload(temp=None),  # null current temperature
    {},  # empty JSON object
])
def test_malformed_payload_returns_none(payload):
    with patch.object(weather.http_requests, "get", return_value=_response(payload)):
        assert weather.fetch_weather() is None


def test_weather_is_cached_between_calls():
    with patch.object(weather.http_requests, "get", return_value=_response(_payload())) as mock_get:
        first = weather.fetch_weather()
        second = weather.fetch_weather()
    assert first == second
    assert mock_get.call_count == 1


def test_failed_fetch_is_not_cached():
    replies = [requests.ConnectionError("down"), _response(_payload())]
    with patch.object(weather.http_requests, "get", side_effect=replies) as mock_get:
        assert weather.fetch_weather() is None
        assert weather.fetch_weather()["temp"] == 72
    assert mock_get.call_count == 2
