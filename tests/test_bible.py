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
    assert b"NIV" in resp.data
    assert b"NLT" in resp.data
    assert b"MSG" in resp.data
    assert b"WEB" not in resp.data


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
    client.set_cookie("bible_last", "NIV/JHN/3")

    resp = client.get("/bible/?book=GEN")
    soup = BeautifulSoup(resp.data, "html.parser")

    assert resp.status_code == 200
    assert soup.select_one("#book-select option[selected]")["value"] == "GEN"


def test_api_chapter_renders(client):
    fake_data = {
        "data": {
            "content": '<p class="s1">The Beginning</p><p class="p">In the beginning</p>',
            "fums_url": None,
        }
    }
    with patch.object(bible_routes, "fetch_bible_chapter", return_value=fake_data):
        resp = client.get("/bible/NIV/GEN/1")

    assert resp.status_code == 200
    assert b"Genesis" in resp.data
    assert b'class="s1"' in resp.data
    assert b'class="p"' in resp.data
    assert b"In the beginning" in resp.data


def test_api_chapter_render_omits_local_verse_number_markup(client):
    fake_data = {"data": {"content": "<p>In the beginning</p>", "fums_url": None}}
    with patch.object(bible_routes, "fetch_bible_chapter", return_value=fake_data):
        resp = client.get("/bible/NIV/GEN/1")
    soup = BeautifulSoup(resp.data, "html.parser")

    assert soup.select_one(".bible-reader article strong") is None
    assert "1 In the beginning" not in soup.select_one(".bible-reader article").get_text(" ")


def test_chapter_includes_home_link(client):
    fake_data = {"data": {"content": "<p>John text</p>", "fums_url": None}}
    with patch.object(bible_routes, "fetch_bible_chapter", return_value=fake_data):
        resp = client.get("/bible/NIV/JHN/1")
    soup = BeautifulSoup(resp.data, "html.parser")
    home_link = soup.find("a", string="Home")

    assert home_link is not None
    assert home_link["href"] == "/"


def test_chapter_nav_uses_canonical_chapter_count_and_go_button(client):
    fake_data = {"data": {"content": "<p>In the beginning</p>", "fums_url": None}}
    with patch.object(bible_routes, "fetch_bible_chapter", return_value=fake_data):
        resp = client.get("/bible/NIV/GEN/1")
    soup = BeautifulSoup(resp.data, "html.parser")
    chapter_options = soup.select("#nav-chapter option")

    assert len(chapter_options) == 50
    assert soup.select_one("#nav-go") is not None


def test_chapter_nav_dropdown_changes_do_not_navigate_before_go(client):
    fake_data = {"data": {"content": "<p>In the beginning</p>", "fums_url": None}}
    with patch.object(bible_routes, "fetch_bible_chapter", return_value=fake_data):
        resp = client.get("/bible/NIV/GEN/1")
    html = resp.data.decode()

    assert "window.location.href" not in html


def test_bible_tap_advance_enabled_keeps_bottom_chapter_buttons(client):
    client.set_cookie("readwise_tap_advance", "on")
    fake_data = {"data": {"content": "<p>John text</p>", "fums_url": None}}

    with patch.object(bible_routes, "fetch_bible_chapter", return_value=fake_data):
        resp = client.get("/bible/NIV/JHN/2")
    soup = BeautifulSoup(resp.data, "html.parser")

    assert soup.select_one("#tap-overlay-top") is None
    assert soup.select_one("#tap-overlay-bottom") is None
    assert "tap-overlay" not in resp.data.decode()
    assert soup.select_one("#bible-reader")["data-prev-url"] == "/bible/NIV/JHN/1"
    assert soup.select_one("#bible-reader")["data-next-url"] == "/bible/NIV/JHN/3"
    prev_link = soup.find("a", string="<")
    next_link = soup.find("a", string=">")
    assert prev_link is not None
    assert prev_link["href"] == "/bible/NIV/JHN/1"
    assert next_link is not None
    assert next_link["href"] == "/bible/NIV/JHN/3"


def test_bible_tap_advance_disabled_keeps_footer_chapter_buttons(client):
    fake_data = {"data": {"content": "<p>John text</p>", "fums_url": None}}
    with patch.object(bible_routes, "fetch_bible_chapter", return_value=fake_data):
        resp = client.get("/bible/NIV/JHN/2")
    soup = BeautifulSoup(resp.data, "html.parser")

    assert soup.select_one("#tap-overlay-top") is None
    prev_link = soup.find("a", string="<")
    next_link = soup.find("a", string=">")
    assert prev_link is not None
    assert prev_link["href"] == "/bible/NIV/JHN/1"
    assert next_link is not None
    assert next_link["href"] == "/bible/NIV/JHN/3"


def test_web_translation_is_not_available(client):
    resp = client.get("/bible/WEB/GEN/1")
    assert resp.status_code == 404
    assert b"Unknown translation" in resp.data


def test_api_bible_chapter_renders(client):
    fake_data = {"data": {"content": "<p>For God so loved the world</p>", "fums_url": None}}
    with patch.object(bible_routes, "fetch_bible_chapter", return_value=fake_data):
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
    assert kwargs["params"]["content-type"] == "html"
    assert kwargs["params"]["include-verse-numbers"] == "false"
    assert kwargs["params"]["include-notes"] == "true"


def test_api_bible_error_renders_error_page(client):
    from app.shared import ReadwiseAPIError

    with patch.object(bible_routes, "fetch_bible_chapter", side_effect=ReadwiseAPIError("API fail")):
        resp = client.get("/bible/NIV/JHN/3")
    assert b"API fail" in resp.data


def test_api_bible_network_error_renders_error(client):
    import requests
    from app.shared import ReadwiseAPIError

    with patch.object(bible_routes, "fetch_bible_chapter", side_effect=ReadwiseAPIError("network fail")):
        resp = client.get("/bible/NIV/JHN/3")
    assert resp.status_code == 502
    assert b"network fail" in resp.data


def test_navigator_shows_only_api_translations_without_api_key(client):
    resp = client.get("/bible/")
    assert b"WEB" not in resp.data
    assert b"NIV" in resp.data
    assert b"NLT" in resp.data
    assert b"MSG" in resp.data
