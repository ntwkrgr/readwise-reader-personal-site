from typing import Any

import requests as http_requests

from app.cache import (
    ARTICLE_CACHE_TTL,
    LIST_CACHE_TTL,
    _article_key,
    _list_key,
    cached_fetch,
    invalidate_article_cache,
    invalidate_list_cache,
)
from app.shared import (
    READWISE_API_BASE,
    ReadwiseAPIError,
    api_get,
    api_headers,
    handle_api_response,
)

ARTICLES_PER_PAGE = 20
READWISE_V2_HIGHLIGHTS = "https://readwise.io/api/v2/highlights/"


def _is_included_new_or_later_item(item: dict[str, Any]) -> bool:
    return (
        item.get("parent_id") is None
        and item.get("location") in {"new", "later"}
        and item.get("category") in {"article", "rss"}
    )


def _fetch_article_list_from_api(
    location: str, page_cursor: str | None, tag: str | None
) -> dict[str, Any]:
    params: dict[str, str | int] = {"location": location, "limit": ARTICLES_PER_PAGE}
    if page_cursor:
        params["pageCursor"] = page_cursor
    if tag:
        params["tag"] = tag
    data = api_get(f"{READWISE_API_BASE}/list/", params=params)
    results = [item for item in data.get("results", []) if _is_included_new_or_later_item(item)]
    return {
        "results": results,
        "nextPageCursor": data.get("nextPageCursor"),
        "count": data.get("count", 0),
    }


def fetch_article_list(
    location: str = "later",
    page_cursor: str | None = None,
    tag: str | None = None,
) -> dict[str, Any]:
    if location == "all":
        return fetch_all_active_articles(page_cursor=page_cursor, tag=tag)
    key = _list_key(location, page_cursor, tag)
    return cached_fetch(
        key, lambda: _fetch_article_list_from_api(location, page_cursor, tag), LIST_CACHE_TTL
    )


def _fetch_all_active_articles_from_api(
    page_cursor: str | None, tag: str | None
) -> dict[str, Any]:
    all_articles: dict[str, dict[str, Any]] = {}
    total_count = 0
    for location in ("later", "new"):
        batch = fetch_article_list(location=location, page_cursor=None, tag=tag)
        for article in batch["results"]:
            article_id = str(article.get("id", ""))
            if article_id:
                all_articles.setdefault(article_id, article)
        total_count += batch.get("count", 0)
    collected = list(all_articles.values())
    return {
        "results": collected[:ARTICLES_PER_PAGE],
        "nextPageCursor": None,
        "count": total_count,
    }


def fetch_all_active_articles(
    page_cursor: str | None = None, tag: str | None = None
) -> dict[str, Any]:
    key = _list_key("all", page_cursor, tag)
    return cached_fetch(
        key, lambda: _fetch_all_active_articles_from_api(page_cursor, tag), LIST_CACHE_TTL
    )


def _fetch_article_from_api(doc_id: str) -> dict[str, Any]:
    params: dict[str, str] = {"id": doc_id, "withHtmlContent": "true"}
    data = api_get(f"{READWISE_API_BASE}/list/", params=params)
    results = data.get("results", [])
    if not results:
        raise ReadwiseAPIError("Article not found.")
    article = results[0]
    if not _is_included_new_or_later_item(article):
        raise ReadwiseAPIError("This reader only shows Articles/RSS saved to New or Later.")
    return article


def fetch_article(doc_id: str) -> dict[str, Any]:
    key = _article_key(doc_id)
    return cached_fetch(key, lambda: _fetch_article_from_api(doc_id), ARTICLE_CACHE_TTL)


def archive_article(doc_id: str) -> None:
    try:
        resp = http_requests.patch(
            f"{READWISE_API_BASE}/update/{doc_id}",
            headers=api_headers(),
            json={"location": "archive"},
            timeout=15,
        )
    except http_requests.RequestException:
        raise ReadwiseAPIError("Could not reach Readwise — check your network connection.")
    handle_api_response(resp)
    invalidate_list_cache()
    invalidate_article_cache(doc_id)


def save_highlight_to_readwise(article: dict[str, Any], text: str, note: str = "") -> None:
    payload = {
        "highlights": [
            {
                "text": text[:8191],
                "title": (article.get("title") or "")[:511],
                "author": (article.get("author") or "")[:1024],
                "source_url": (article.get("source_url") or article.get("url") or "")[:2047],
                "category": "articles",
            }
        ]
    }
    if note:
        payload["highlights"][0]["note"] = note[:8191]
    try:
        resp = http_requests.post(
            READWISE_V2_HIGHLIGHTS,
            headers=api_headers(),
            json=payload,
            timeout=15,
        )
    except http_requests.RequestException:
        raise ReadwiseAPIError("Could not reach Readwise — check your network connection.")
    handle_api_response(resp)
