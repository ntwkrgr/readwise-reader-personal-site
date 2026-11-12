"""Current weather for the home page hero card, from Open-Meteo (free, no API key)."""

import os
from typing import Any

import requests as http_requests

from app.cache import cached_fetch

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
# Location for the weather card; defaults to San Angelo, TX (override in .env)
WEATHER_LAT = os.environ.get("WEATHER_LAT", "31.4638")
WEATHER_LON = os.environ.get("WEATHER_LON", "-100.4370")
WEATHER_LOCATION = os.environ.get("WEATHER_LOCATION", "San Angelo")
WEATHER_CACHE_TTL = 1800  # 30 minutes
WEATHER_TIMEOUT = 5  # seconds to wait for Open-Meteo before giving up

# WMO weather code -> (condition label, icon name drawn by templates/_weather_icons.html)
WMO_CODES: dict[int, tuple[str, str]] = {
    0: ("Clear", "clear"),
    1: ("Mostly clear", "partly"),
    2: ("Partly cloudy", "partly"),
    3: ("Overcast", "cloudy"),
    45: ("Fog", "fog"),
    48: ("Fog", "fog"),
    51: ("Drizzle", "rain"),
    53: ("Drizzle", "rain"),
    55: ("Drizzle", "rain"),
    56: ("Freezing drizzle", "rain"),
    57: ("Freezing drizzle", "rain"),
    61: ("Light rain", "rain"),
    63: ("Rain", "rain"),
    65: ("Heavy rain", "rain"),
    66: ("Freezing rain", "rain"),
    67: ("Freezing rain", "rain"),
    71: ("Light snow", "snow"),
    73: ("Snow", "snow"),
    75: ("Heavy snow", "snow"),
    77: ("Snow grains", "snow"),
    80: ("Showers", "rain"),
    81: ("Showers", "rain"),
    82: ("Heavy showers", "rain"),
    85: ("Snow showers", "snow"),
    86: ("Snow showers", "snow"),
    95: ("Thunderstorm", "storm"),
    96: ("Thunderstorm", "storm"),
    99: ("Thunderstorm", "storm"),
}


def _fetch_current() -> dict[str, Any]:
    """Call Open-Meteo and reduce the reply to the fields the hero card shows; raises on any failure."""
    resp = http_requests.get(
        OPEN_METEO_URL,
        params={
            "latitude": WEATHER_LAT,
            "longitude": WEATHER_LON,
            "current": "temperature_2m,weather_code,is_day",
            "daily": "temperature_2m_max,temperature_2m_min",
            "temperature_unit": "fahrenheit",
            "timezone": "auto",
            "forecast_days": 1,
        },
        timeout=WEATHER_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    current, daily = data["current"], data["daily"]
    condition, icon = WMO_CODES.get(current["weather_code"], ("Unknown", "cloudy"))
    # Clear sky at night gets a moon instead of a sun
    if icon == "clear" and not current["is_day"]:
        icon = "night"
    return {
        "temp": round(current["temperature_2m"]),
        "high": round(daily["temperature_2m_max"][0]),
        "low": round(daily["temperature_2m_min"][0]),
        "condition": condition,
        "icon": icon,
        "location": WEATHER_LOCATION,
    }


def fetch_weather() -> dict[str, Any] | None:
    """Return current weather (cached 30 min), or None when it can't be fetched so the home page still renders."""
    try:
        return cached_fetch(f"weather:{WEATHER_LAT}:{WEATHER_LON}", _fetch_current, WEATHER_CACHE_TTL)
    except Exception:  # Network, HTTP, or payload problems all just hide the weather
        return None
