"""Tests for bible blueprint."""
import pytest
from unittest.mock import patch

import diskcache

from app import create_app
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


def test_web_chapter_renders(client):
    resp = client.get("/bible/WEB/GEN/1")
    assert resp.status_code == 200
    assert b"Genesis" in resp.data


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
