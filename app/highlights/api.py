from typing import Any

from app.cache import cached_fetch
from app.shared import api_get

HIGHLIGHTS_CACHE_TTL = 1200  # 20 minutes
BOOKS_PAGE_SIZE = 1000  # Readwise max for Book LIST; that endpoint is limited to 20 requests/minute

READWISE_V2_BASE = "https://readwise.io/api/v2"


def fetch_highlights(page: int = 1) -> dict[str, Any]:
    key = f"highlights:page:{page}"
    return cached_fetch(
        key,
        lambda: api_get(
            f"{READWISE_V2_BASE}/highlights/",
            {"page": page, "page_size": 20},
        ),
        HIGHLIGHTS_CACHE_TTL,
    )


def fetch_books() -> dict[str, Any]:
    key = "highlights:books:all"

    def fetch_all_books() -> dict[str, Any]:
        all_results: list[dict[str, Any]] = []
        combined: dict[str, Any] | None = None
        page = 1

        # Request numbered pages at the max page size until Readwise reports no next page.
        while page:
            data = api_get(f"{READWISE_V2_BASE}/books/", {"page": page, "page_size": BOOKS_PAGE_SIZE})
            if combined is None:
                combined = dict(data)
            all_results.extend(data.get("results", []))
            page = page + 1 if data.get("next") else None

        if combined is None:
            combined = {"results": [], "next": None}
        combined["results"] = all_results
        combined["next"] = None
        return combined

    return cached_fetch(
        key,
        fetch_all_books,
        HIGHLIGHTS_CACHE_TTL,
    )


def fetch_daily_review() -> dict[str, Any]:
    # Daily review is not cached because it changes daily and is lightweight.
    return api_get(f"{READWISE_V2_BASE}/review/")
