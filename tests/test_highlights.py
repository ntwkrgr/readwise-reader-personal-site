"""Tests for highlights blueprint."""
import diskcache
import pytest
from unittest.mock import patch

from app import create_app
from app import cache as cache_module
import app.highlights.api as highlights_api
import app.highlights.routes as highlights_routes
from app.shared import ReadwiseAPIError

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
    "review_id": 123,
    "review_url": "https://readwise.io/reviews/123",
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
            resp = client.get("/highlights/all")
    assert resp.status_code == 200
    assert b"Great quote from a book" in resp.data
    assert b"Great Book" in resp.data
    assert b"Great Author" in resp.data


def test_highlights_list_api_error_renders_error(client):
    from app.shared import ReadwiseAPIError

    with patch.object(highlights_routes, "fetch_highlights", side_effect=ReadwiseAPIError("API down")):
        with patch.object(highlights_routes, "fetch_books", side_effect=ReadwiseAPIError("API down")):
            resp = client.get("/highlights/all")
    assert b"API down" in resp.data


def test_highlights_list_invalid_page_falls_back(client):
    """?page=abc should not cause 500."""
    with patch.object(highlights_routes, "fetch_highlights", return_value=SAMPLE_HIGHLIGHTS_DATA):
        with patch.object(highlights_routes, "fetch_books", return_value=SAMPLE_BOOKS_DATA):
            resp = client.get("/highlights/all?page=abc")
    assert resp.status_code == 200


def test_highlights_list_renders_previous_and_next_page_buttons(client):
    paged_data = {**SAMPLE_HIGHLIGHTS_DATA, "next": "next-url"}
    with patch.object(highlights_routes, "fetch_highlights", return_value=paged_data):
        with patch.object(highlights_routes, "fetch_books", return_value=SAMPLE_BOOKS_DATA):
            resp = client.get("/highlights/all?page=2")

    assert b"Previous page" in resp.data
    assert b"/highlights/all?page=1" in resp.data
    assert b"Next page" in resp.data
    assert b"/highlights/all?page=3" in resp.data


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
            resp = client.get("/highlights/")
    assert resp.status_code == 200
    assert b"Great quote from a book" in resp.data
    assert b"Great Book" in resp.data
    assert b"Great Author" in resp.data
    assert b"https://readwise.io/reviews/123" in resp.data
    assert b"All highlights" in resp.data


def test_daily_review_builds_review_url_from_id_when_url_missing(client):
    review_data = {**SAMPLE_REVIEW_DATA, "review_url": None, "review_id": 456}
    with patch.object(highlights_routes, "fetch_daily_review", return_value=review_data):
        with patch.object(highlights_routes, "fetch_books", return_value=SAMPLE_BOOKS_DATA):
            resp = client.get("/highlights/")

    assert b"https://readwise.io/reviews/456" in resp.data
    assert b'href="https://readwise.io/review"' not in resp.data


def test_daily_review_legacy_url_still_renders(client):
    with patch.object(highlights_routes, "fetch_daily_review", return_value=SAMPLE_REVIEW_DATA):
        with patch.object(highlights_routes, "fetch_books", return_value=SAMPLE_BOOKS_DATA):
            resp = client.get("/highlights/review")

    assert resp.status_code == 200
    assert b"Daily Review" in resp.data


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


def test_highlight_of_the_day_picks_one_review_highlight_and_caches_it(client):
    review = {"highlights": [
        {"text": "First", "title": "Book A", "author": "Author A"},
        {"text": "Second", "title": "Book B", "author": None},
    ]}
    with patch.object(highlights_api, "api_get", return_value=review) as mock_api_get:
        first = highlights_api.fetch_highlight_of_the_day()
        second = highlights_api.fetch_highlight_of_the_day()
    assert mock_api_get.call_count == 1
    assert first == second
    assert first in (
        {"text": "First", "title": "Book A", "author": "Author A"},
        {"text": "Second", "title": "Book B", "author": None},
    )


def test_highlight_of_the_day_is_none_when_review_is_empty(client):
    with patch.object(highlights_api, "api_get", return_value={"highlights": []}):
        assert highlights_api.fetch_highlight_of_the_day() is None


def test_highlight_of_the_day_is_none_on_api_error(client):
    with patch.object(highlights_api, "api_get", side_effect=ReadwiseAPIError("API down")):
        assert highlights_api.fetch_highlight_of_the_day() is None


# Book titles Readwise imports sometimes arrive HTML-escaped, even with title-cased entity names
ENCODED_BOOK = {**SAMPLE_BOOK, "title": "Let&#39;s Dance", "author": "Black &Amp; Decker"}


def test_decode_entities_handles_readwise_encoded_text():
    from app.shared import decode_entities

    assert decode_entities("Let&#39;s Dance") == "Let's Dance"
    assert decode_entities("Black &Amp; Decker") == "Black & Decker"
    assert decode_entities("Fish &amp; Chips &quot;now&quot;") == 'Fish & Chips "now"'
    assert decode_entities("Plain & simple, it's fine") == "Plain & simple, it's fine"
    assert decode_entities(None) is None


def test_highlights_list_decodes_encoded_book_titles(client):
    with patch.object(highlights_routes, "fetch_highlights", return_value=SAMPLE_HIGHLIGHTS_DATA):
        with patch.object(highlights_routes, "fetch_books", return_value={"results": [ENCODED_BOOK]}):
            html = client.get("/highlights/all").get_data(as_text=True)
    assert "Let&#39;s Dance" in html and "Black &amp; Decker" in html
    assert "&amp;#39;" not in html and "&amp;Amp;" not in html


def test_daily_review_decodes_encoded_source_titles(client):
    with patch.object(highlights_routes, "fetch_daily_review", return_value=SAMPLE_REVIEW_DATA):
        with patch.object(highlights_routes, "fetch_books", return_value={"results": [ENCODED_BOOK]}):
            html = client.get("/highlights/").get_data(as_text=True)
    assert "Let&#39;s Dance" in html and "Black &amp; Decker" in html
    assert "&amp;#39;" not in html and "&amp;Amp;" not in html
