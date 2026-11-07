"""Tests for the home page."""
from pathlib import Path

import pytest

from app import create_app

DASHBOARD_TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "dashboard.html"
# (accent class, card title, link) for each home page card, in page order
SECTION_CARDS = (
    ("card-reader", "Reader", "/reader/"),
    ("card-highlights", "Highlights", "/highlights/"),
    ("card-notebook", "Notebook", "/notebook/"),
    ("card-settings", "Settings", "/settings"),
)


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
