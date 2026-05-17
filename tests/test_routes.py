"""Integration tests for Flask routes."""
import time
import diskcache
import pytest
from unittest.mock import patch

from app import create_app
from app import cache as cache_module
from app.reader import routes as routes_module
from app.shared import ReadwiseAPIError


SAMPLE_ARTICLE = {
    "id": "abc123",
    "title": "Test Article",
    "author": "Test Author",
    "word_count": 500,
    "reading_time": "3 min",
    "reading_progress": 0.25,
    "tags": {},
    "saved_at": "2024-01-01T00:00:00Z",
    "created_at": "2024-01-01T00:00:00Z",
    "location": "later",
    "category": "article",
    "parent_id": None,
    "html_content": "<p>Hello world</p>",
    "source_url": "https://example.com/article",
}

SAMPLE_LIST = {
    "results": [SAMPLE_ARTICLE],
    "nextPageCursor": None,
    "count": 1,
}


@pytest.fixture
def client(tmp_path):
    flask_app = create_app({"TESTING": True})
    cache = diskcache.Cache(str(tmp_path / "cache"))
    with patch.object(cache_module, "_cache", cache):
        with flask_app.test_client() as c:
            yield c
    cache.close()


# --- Article list ---

def test_dashboard_renders_feature_links(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Reader" in resp.data
    assert b"Highlights" in resp.data
    assert b"Bible" in resp.data
    assert b"Settings" in resp.data


def test_list_renders_articles(client):
    with patch.object(routes_module, "fetch_article_list", return_value=SAMPLE_LIST):
        resp = client.get("/reader/")
    assert resp.status_code == 200
    assert b"Test Article" in resp.data


def test_list_defaults_to_all_location(client):
    with patch.object(routes_module, "fetch_article_list", return_value=SAMPLE_LIST) as mock:
        client.get("/reader/")
    mock.assert_called_once_with(location="all", page_cursor=None, tag=None)


def test_list_passes_location_param(client):
    with patch.object(routes_module, "fetch_article_list", return_value=SAMPLE_LIST) as mock:
        client.get("/reader/?location=later")
    mock.assert_called_once_with(location="later", page_cursor=None, tag=None)


def test_list_invalid_location_falls_back_to_all(client):
    with patch.object(routes_module, "fetch_article_list", return_value=SAMPLE_LIST) as mock:
        client.get("/reader/?location=bogus")
    mock.assert_called_once_with(location="all", page_cursor=None, tag=None)


def test_list_shows_cache_age_when_refreshed(client):
    cache_module._cache.set("last_refresh", time.time() - 300)  # 5 min ago
    with patch.object(routes_module, "fetch_article_list", return_value=SAMPLE_LIST):
        resp = client.get("/reader/")
    assert b"5m ago" in resp.data


def test_list_shows_just_now_when_very_recent(client):
    cache_module._cache.set("last_refresh", time.time() - 10)
    with patch.object(routes_module, "fetch_article_list", return_value=SAMPLE_LIST):
        resp = client.get("/reader/")
    assert b"just now" in resp.data


def test_list_api_error_renders_error_page(client):
    with patch.object(routes_module, "fetch_article_list", side_effect=ReadwiseAPIError("API down")):
        resp = client.get("/reader/")
    assert b"API down" in resp.data


# --- Refresh cooldown ---

def test_refresh_clears_cache_when_allowed(client):
    cache_module._cache.set("last_refresh", time.time() - 200)
    with patch.object(routes_module, "fetch_article_list", return_value=SAMPLE_LIST):
        with patch.object(routes_module, "invalidate_list_cache") as mock_inv:
            client.get("/reader/?refresh=1")
    mock_inv.assert_called_once()


def test_refresh_skipped_within_cooldown(client):
    cache_module._cache.set("last_refresh", time.time())  # Just refreshed
    with patch.object(routes_module, "fetch_article_list", return_value=SAMPLE_LIST):
        with patch.object(routes_module, "invalidate_list_cache") as mock_inv:
            resp = client.get("/reader/?refresh=1")
    mock_inv.assert_not_called()
    assert b"recently" in resp.data  # Flash message shown


# --- Read article ---

def test_read_article_renders_content(client):
    with patch.object(routes_module, "fetch_article", return_value=SAMPLE_ARTICLE):
        resp = client.get("/reader/read/abc123")
    assert resp.status_code == 200
    assert b"Test Article" in resp.data
    assert b"Hello world" in resp.data


def test_read_article_strips_images(client):
    article = {**SAMPLE_ARTICLE, "html_content": "<p>Text</p><img src='bad.jpg'><p>More</p>"}
    with patch.object(routes_module, "fetch_article", return_value=article):
        resp = client.get("/reader/read/abc123")
    assert b"<img" not in resp.data
    assert b"Text" in resp.data
    assert b"More" in resp.data


def test_read_article_api_error_renders_error_page(client):
    with patch.object(routes_module, "fetch_article", side_effect=ReadwiseAPIError("Not found")):
        resp = client.get("/reader/read/missing")
    assert b"Not found" in resp.data


def test_highlight_rejects_empty_selection(client):
    resp = client.post("/reader/read/abc123/highlight", data={"text": ""})
    assert resp.status_code == 302


def test_highlight_saves_to_readwise(client):
    with patch.object(routes_module, "fetch_article", return_value=SAMPLE_ARTICLE):
        with patch.object(routes_module, "save_highlight_to_readwise") as mock_save:
            resp = client.post("/reader/read/abc123/highlight", data={"text": "Great quote"})
    mock_save.assert_called_once()
    assert resp.status_code == 302


# --- Archive ---

def test_archive_redirects_on_success(client):
    with patch.object(routes_module, "archive_article"):
        resp = client.post("/reader/archive/abc123")
    assert resp.status_code == 302
    assert "/reader/" in resp.headers["Location"]


def test_archive_api_error_renders_error_page(client):
    with patch.object(routes_module, "archive_article", side_effect=ReadwiseAPIError("Failed")):
        resp = client.post("/reader/archive/abc123")
    assert b"Failed" in resp.data


# --- Settings ---

def test_settings_get_renders(client):
    resp = client.get("/settings")
    assert resp.status_code == 200


def test_settings_post_sets_cookies_and_redirects(client):
    resp = client.post("/settings", data={
        "text_size": "large",
        "text_weight": "bold",
        "theme": "dark",
        "tap_advance": "on",
        "default_sort": "oldest",
    })
    assert resp.status_code == 302
    set_cookies = "\n".join(resp.headers.getlist("Set-Cookie"))
    assert "readwise_text_size=large" in set_cookies
    assert "readwise_theme=dark" in set_cookies


def test_settings_post_rejects_invalid_values(client):
    resp = client.post("/settings", data={
        "text_size": "HUGE",
        "text_weight": "normal",
        "theme": "light",
        "tap_advance": "off",
        "default_sort": "newest",
    })
    assert resp.status_code == 302
    set_cookies = "\n".join(resp.headers.getlist("Set-Cookie"))
    assert "readwise_text_size=medium" in set_cookies  # Falls back to default
