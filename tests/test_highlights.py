"""Tests for highlights blueprint."""
import diskcache
import pytest
from unittest.mock import patch

from app import create_app
from app import cache as cache_module
import app.highlights.api as highlights_api
import app.highlights.routes as highlights_routes

SAMPLE_HIGHLIGHT = {
    "id": 1,
    "text": "Great quote from a book",
    "book_id": 42,
    "note": "",
    "url": None,
}

SAMPLE_BOOK = {
    "id": 42,
    "title": "Great Book",
    "author": "Great Author",
    "category": "books",
}

SAMPLE_HIGHLIGHTS_DATA = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [SAMPLE_HIGHLIGHT],
}

SAMPLE_BOOKS_DATA = {
    "count": 1,
    "next": None,
    "results": [SAMPLE_BOOK],
}

SAMPLE_REVIEW_DATA = {
    "highlights": [SAMPLE_HIGHLIGHT],
    "review_url": "https://readwise.io/review",
}


@pytest.fixture
def client(tmp_path):
    app = create_app({"TESTING": True})
    cache = diskcache.Cache(str(tmp_path / "cache"))
    with patch.object(cache_module, "_cache", cache):
        with app.test_client() as c:
            yield c
    cache.close()


def test_highlights_list_renders(client):
    with patch.object(highlights_routes, "fetch_highlights", return_value=SAMPLE_HIGHLIGHTS_DATA):
        with patch.object(highlights_routes, "fetch_books", return_value=SAMPLE_BOOKS_DATA):
            resp = client.get("/highlights/")
    assert resp.status_code == 200
    assert b"Great quote from a book" in resp.data
    assert b"Great Book" in resp.data
    assert b"Great Author" in resp.data


def test_highlights_list_api_error_renders_error(client):
    from app.shared import ReadwiseAPIError

    with patch.object(highlights_routes, "fetch_highlights", side_effect=ReadwiseAPIError("API down")):
        with patch.object(highlights_routes, "fetch_books", side_effect=ReadwiseAPIError("API down")):
            resp = client.get("/highlights/")
    assert b"API down" in resp.data


def test_highlights_list_invalid_page_falls_back(client):
    """?page=abc should not cause 500."""
    with patch.object(highlights_routes, "fetch_highlights", return_value=SAMPLE_HIGHLIGHTS_DATA):
        with patch.object(highlights_routes, "fetch_books", return_value=SAMPLE_BOOKS_DATA):
            resp = client.get("/highlights/?page=abc")
    assert resp.status_code == 200


def test_fetch_books_paginates_and_caches_all_results(client):
    second_book = {**SAMPLE_BOOK, "id": 43, "title": "Second Book"}
    next_url = "https://readwise.io/api/v2/books/?page=2"
    first_page = {"count": 2, "next": next_url, "results": [SAMPLE_BOOK]}
    second_page = {"count": 2, "next": None, "results": [second_book]}

    with patch.object(highlights_api, "api_get", side_effect=[first_page, second_page]) as mock_api_get:
        data = highlights_api.fetch_books()

    assert data["results"] == [SAMPLE_BOOK, second_book]
    assert data["next"] is None
    assert cache_module._cache.get("highlights:books:all") == data
    assert mock_api_get.call_args_list[0].args == (f"{highlights_api.READWISE_V2_BASE}/books/",)
    assert mock_api_get.call_args_list[1].args == (next_url,)


def test_daily_review_renders(client):
    with patch.object(highlights_routes, "fetch_daily_review", return_value=SAMPLE_REVIEW_DATA):
        with patch.object(highlights_routes, "fetch_books", return_value=SAMPLE_BOOKS_DATA):
            resp = client.get("/highlights/review")
    assert resp.status_code == 200
    assert b"Great quote from a book" in resp.data
    assert b"Great Book" in resp.data
    assert b"Great Author" in resp.data
    assert b"readwise.io/review" in resp.data


def test_daily_review_uses_review_highlight_source_metadata(client):
    review_data = {
        "highlights": [{
            **SAMPLE_HIGHLIGHT,
            "book_id": None,
            "title": "Review Article",
            "author": "Review Author",
        }],
    }

    with patch.object(highlights_routes, "fetch_daily_review", return_value=review_data):
        with patch.object(highlights_routes, "fetch_books", return_value={"results": []}):
            resp = client.get("/highlights/review")

    assert b"Review Article" in resp.data
    assert b"Review Author" in resp.data


def test_daily_review_api_error_renders_error(client):
    from app.shared import ReadwiseAPIError

    with patch.object(highlights_routes, "fetch_daily_review", side_effect=ReadwiseAPIError("Fail")):
        resp = client.get("/highlights/review")
    assert b"Fail" in resp.data
