from typing import Any

from app.cache import cached_fetch
from app.shared import api_get

HIGHLIGHTS_CACHE_TTL = 1200  # 20 minutes

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
    key = "highlights:books"
    return cached_fetch(
        key,
        lambda: api_get(f"{READWISE_V2_BASE}/books/"),
        HIGHLIGHTS_CACHE_TTL,
    )


def fetch_daily_review() -> dict[str, Any]:
    # Daily review is not cached because it changes daily and is lightweight.
    return api_get(f"{READWISE_V2_BASE}/review/")
