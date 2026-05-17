"""Tests for highlights blueprint."""
import pytest
from unittest.mock import patch

from app import create_app
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
    with app.test_client() as c:
        yield c


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


def test_daily_review_renders(client):
    with patch.object(highlights_routes, "fetch_daily_review", return_value=SAMPLE_REVIEW_DATA):
        resp = client.get("/highlights/review")
    assert resp.status_code == 200
    assert b"Great quote from a book" in resp.data
    assert b"readwise.io/review" in resp.data


def test_daily_review_api_error_renders_error(client):
    from app.shared import ReadwiseAPIError

    with patch.object(highlights_routes, "fetch_daily_review", side_effect=ReadwiseAPIError("Fail")):
        resp = client.get("/highlights/review")
    assert b"Fail" in resp.data
