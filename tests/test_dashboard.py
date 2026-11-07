"""Tests for the home page."""
from pathlib import Path
from unittest.mock import patch

import pytest

from app import create_app
from app import dashboard as dashboard_module
from app import weather

DASHBOARD_TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "dashboard.html"
# (accent class, card title, link) for each home page card, in page order
SECTION_CARDS = (
    ("card-reader", "Reader", "/reader/"),
    ("card-highlights", "Highlights", "/highlights/"),
    ("card-notebook", "Notebook", "/notebook/"),
    ("card-settings", "Settings", "/settings"),
)
# What fetch_weather() returns on a good day
SAMPLE_WEATHER = {
    "temp": 72,
    "high": 78,
    "low": 55,
    "condition": "Partly cloudy",
    "icon": "partly",
    "location": "San Angelo",
}


@pytest.fixture
def client():
    flask_app = create_app({"TESTING": True})
    with flask_app.test_client() as c:
        yield c


def _home_html(client):
    """GET the home page, check it rendered, and return its HTML."""
    resp = client.get("/")
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def _home_with_weather(client, weather_data):
    """GET the home page with fetch_weather() stubbed to return weather_data."""
    with patch.object(dashboard_module, "fetch_weather", return_value=weather_data):
        return _home_html(client)


def test_section_cards_link_to_each_tool_in_order(client):
    html = _home_html(client)
    positions = [html.index(f'href="{href}"') for _, _, href in SECTION_CARDS]
    assert positions == sorted(positions)


def test_each_section_card_has_accent_icon_and_label(client):
    html = _home_html(client)
    for card_class, label, _ in SECTION_CARDS:
        assert f'class="dashboard-card {card_class}' in html
        assert f'<span class="dashboard-card-title">{label}</span>' in html
    assert html.count('<span class="dashboard-card-icon"><svg') == len(SECTION_CARDS)


def test_settings_card_is_pinned_to_the_bottom(client):
    html = _home_html(client)
    assert 'class="dashboard-card card-settings dashboard-settings-link"' in html
    assert "margin-top: auto" in html


def test_old_plain_link_list_is_gone(client):
    assert "dashboard-link" not in _home_html(client)


def test_dark_theme_keeps_colored_stripes():
    """Dark rules must recolor borders side by side; a `border-color` shorthand would also turn the colored left stripe white."""
    assert "border-color:" not in DASHBOARD_TEMPLATE.read_text()


def test_weather_card_shows_current_conditions(client):
    html = _home_with_weather(client, SAMPLE_WEATHER)
    assert 'class="weather-card wx-partly"' in html
    assert '<div class="weather-temp">72°</div>' in html
    assert "Partly cloudy" in html
    assert "H 78° · L 55° · San Angelo" in html


def test_weather_card_comes_first_with_no_heading_above_it(client):
    html = _home_with_weather(client, SAMPLE_WEATHER)
    assert html.index('class="weather-card') < html.index('class="dashboard-card')
    assert "dashboard-title" not in html


def test_weather_unavailable_still_renders_home(client):
    html = _home_with_weather(client, None)
    assert 'class="weather-card weather-card-empty"' in html
    assert "Weather unavailable" in html
    for _, _, href in SECTION_CARDS:
        assert f'href="{href}"' in html


def test_every_weather_icon_has_an_svg():
    flask_app = create_app({"TESTING": True})
    with flask_app.app_context():
        weather_icon = flask_app.jinja_env.get_template("_weather_icons.html").module.weather_icon
        names = {icon for _, icon in weather.WMO_CODES.values()} | {"night"}
        for name in sorted(names):
            assert "<svg" in str(weather_icon(name)), f"no SVG for weather icon {name!r}"
