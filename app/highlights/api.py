import random
from datetime import date
from typing import Any

from app.cache import cached_fetch
from app.shared import ReadwiseAPIError, api_get

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
    key = "highlights:books:all"

    def fetch_all_books() -> dict[str, Any]:
        url = f"{READWISE_V2_BASE}/books/"
        all_results: list[dict[str, Any]] = []
        combined: dict[str, Any] | None = None

        while url:
            data = api_get(url)
            if combined is None:
                combined = dict(data)
            all_results.extend(data.get("results", []))
            url = data.get("next")

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


def fetch_highlight_of_the_day() -> dict[str, Any] | None:
    """Return one random Daily Review highlight (text, title, author) for the home page, or None.

    The pick is cached per calendar day so the home page shows the same highlight all day
    and makes at most one Readwise call per day. Errors and empty reviews return None.
    """

    def pick() -> dict[str, Any] | None:
        # Choose one highlight from today's review and keep only the fields the card shows
        highlights = fetch_daily_review().get("highlights") or []
        if not highlights:
            return None
        chosen = random.choice(highlights)
        return {"text": chosen.get("text"), "title": chosen.get("title"), "author": chosen.get("author")}

    try:
        return cached_fetch(f"highlights:home:{date.today().isoformat()}", pick, 86400)
    except ReadwiseAPIError:  # Readwise down or rate-limited: just hide the card
        return None
