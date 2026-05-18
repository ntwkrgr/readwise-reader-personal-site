"""Tests for bible blueprint."""
import pytest
from unittest.mock import patch

import diskcache
from bs4 import BeautifulSoup

from app import create_app
import app.bible.api as bible_api
import app.bible.routes as bible_routes
import app.cache as cache_module


@pytest.fixture
def client(tmp_path):
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    cache = diskcache.Cache(str(tmp_path / "cache"))
    with patch.object(cache_module, "_cache", cache):
        with flask_app.test_client() as c:
            yield c
    cache.close()


def test_navigator_renders(client):
    resp = client.get("/bible/")
    assert resp.status_code == 200
    assert b"WEB" in resp.data


def test_navigator_includes_home_link(client):
    resp = client.get("/bible/?book=JHN")
    soup = BeautifulSoup(resp.data, "html.parser")
    home_link = soup.find("a", string="Home")

    assert home_link is not None
    assert home_link["href"] == "/"


def test_navigator_uses_canonical_chapter_count_for_selected_book(client):
    resp = client.get("/bible/?book=GEN")
    soup = BeautifulSoup(resp.data, "html.parser")
    chapter_options = soup.select("#chapter-select option")

    assert len(chapter_options) == 50


def test_navigator_dropdown_changes_do_not_navigate_before_go(client):
    resp = client.get("/bible/?book=GEN")
    html = resp.data.decode()
    soup = BeautifulSoup(html, "html.parser")

    assert soup.select_one("#go-button") is not None
    assert "window.location.href" not in html


def test_navigator_query_parameters_override_saved_position(client):
    client.set_cookie("bible_last", "WEB/JHN/3")

    resp = client.get("/bible/?book=GEN")
    soup = BeautifulSoup(resp.data, "html.parser")

    assert resp.status_code == 200
    assert soup.select_one("#book-select option[selected]")["value"] == "GEN"


def test_web_chapter_renders(client):
    resp = client.get("/bible/WEB/GEN/1")
    assert resp.status_code == 200
    assert b"Genesis" in resp.data


def test_web_chapter_omits_verse_numbers(client):
    resp = client.get("/bible/WEB/GEN/1")
    soup = BeautifulSoup(resp.data, "html.parser")

    assert soup.select_one(".bible-reader article strong") is None
    assert "1 In the beginning" not in soup.select_one(".bible-reader article").get_text(" ")


def test_chapter_includes_home_link(client):
    resp = client.get("/bible/WEB/JHN/1")
    soup = BeautifulSoup(resp.data, "html.parser")
    home_link = soup.find("a", string="Home")

    assert home_link is not None
    assert home_link["href"] == "/"


def test_chapter_nav_uses_canonical_chapter_count_and_go_button(client):
    resp = client.get("/bible/WEB/GEN/1")
    soup = BeautifulSoup(resp.data, "html.parser")
    chapter_options = soup.select("#nav-chapter option")

    assert len(chapter_options) == 50
    assert soup.select_one("#nav-go") is not None


def test_chapter_nav_dropdown_changes_do_not_navigate_before_go(client):
    resp = client.get("/bible/WEB/GEN/1")
    html = resp.data.decode()

    assert "window.location.href" not in html


def test_bible_tap_advance_enabled_replaces_footer_chapter_buttons(client):
    client.set_cookie("readwise_tap_advance", "on")

    resp = client.get("/bible/WEB/JHN/2")
    soup = BeautifulSoup(resp.data, "html.parser")

    assert soup.select_one("#tap-overlay-top") is not None
    assert soup.select_one("#tap-overlay-bottom") is not None
    assert soup.select_one("#bible-reader")["data-prev-url"] == "/bible/WEB/JHN/1"
    assert soup.select_one("#bible-reader")["data-next-url"] == "/bible/WEB/JHN/3"
    assert "Next \u2192" not in resp.data.decode()
    assert "\u2190 Previous" not in resp.data.decode()


def test_bible_tap_advance_disabled_keeps_footer_chapter_buttons(client):
    resp = client.get("/bible/WEB/JHN/2")
    soup = BeautifulSoup(resp.data, "html.parser")

    assert soup.select_one("#tap-overlay-top") is None
    assert b"Next \xe2\x86\x92" in resp.data
    assert b"\xe2\x86\x90 Previous" in resp.data


def test_web_chapter_not_found_renders_error(client):
    resp = client.get("/bible/WEB/GEN/999")
    assert resp.status_code == 404
    assert b"not found" in resp.data


def test_api_bible_chapter_renders(client):
    fake_data = {"data": {"content": "<p>For God so loved the world</p>", "fums_url": None}}
    with patch.object(bible_routes, "fetch_bible_chapter", return_value=fake_data):
        with patch.object(bible_routes, "bible_api_available", return_value=True):
            resp = client.get("/bible/NIV/JHN/3")
    assert resp.status_code == 200
    assert b"For God so loved the world" in resp.data


def test_api_bible_fetch_omits_verse_numbers(client):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"data": {"content": "For God so loved the world"}}

    with patch.object(bible_api, "BIBLE_API_KEY", "test-key"):
        with patch.object(bible_api.http_requests, "get", return_value=FakeResponse()) as mock_get:
            bible_api.fetch_bible_chapter("NIV", "JHN", 3)

    _, kwargs = mock_get.call_args
    assert kwargs["params"]["include-verse-numbers"] == "false"


def test_api_bible_error_renders_error_page(client):
    from app.shared import ReadwiseAPIError

    with patch.object(bible_routes, "fetch_bible_chapter", side_effect=ReadwiseAPIError("API fail")):
        with patch.object(bible_routes, "bible_api_available", return_value=True):
            resp = client.get("/bible/NIV/JHN/3")
    assert b"API fail" in resp.data


def test_api_bible_network_error_renders_error(client):
    import requests
    from app.shared import ReadwiseAPIError

    with patch.object(bible_routes, "fetch_bible_chapter", side_effect=ReadwiseAPIError("network fail")):
        with patch.object(bible_routes, "bible_api_available", return_value=True):
            resp = client.get("/bible/NIV/JHN/3")
    assert resp.status_code == 502
    assert b"network fail" in resp.data


def test_navigator_only_shows_web_without_api_key(client):
    with patch.object(bible_routes, "bible_api_available", return_value=False):
        resp = client.get("/bible/")
    assert b"WEB" in resp.data
    assert b"NIV" not in resp.data
