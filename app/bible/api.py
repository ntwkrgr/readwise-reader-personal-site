import os
import requests as http_requests
from typing import Any

from app.cache import cached_fetch
from app.shared import ReadwiseAPIError

BIBLE_API_KEY = os.environ.get("BIBLE_API_KEY", "")
BIBLE_API_BASE = "https://api.scripture.api.bible/v1"
BIBLE_CACHE_TTL = int(os.environ.get("BIBLE_CACHE_TTL", 1209600))
TRANSLATION_IDS: dict[str, str] = {
    'NIV': '78a9f6124f344018-01',  # verified NIV ID
    # NOTE: NLT and MSG IDs below are placeholders — verify at api.bible/bibles before deploying
    'NLT': 'nlt-placeholder-verify',
    'MSG': 'msg-placeholder-verify',
}


def is_available() -> bool:
    return bool(BIBLE_API_KEY)


def fetch_bible_chapter(translation: str, book_id: str, chapter: int) -> dict[str, Any]:
    if not BIBLE_API_KEY:
        raise ReadwiseAPIError("Bible API key not configured.")
    bible_id = TRANSLATION_IDS.get(translation)
    if not bible_id:
        raise ReadwiseAPIError(f"Unknown translation: {translation}")
    key = f"bible:{translation}:{book_id}:{chapter}"

    def _fetch() -> dict[str, Any]:
        try:
            resp = http_requests.get(
                f"{BIBLE_API_BASE}/bibles/{bible_id}/chapters/{book_id}.{chapter}",
                headers={"api-key": BIBLE_API_KEY},
                params={"content-type": "text", "include-verse-numbers": "true"},
                timeout=15,
            )
        except http_requests.RequestException:
            raise ReadwiseAPIError('Could not reach Bible API — check your network connection.')
        if resp.status_code == 401:
            raise ReadwiseAPIError("Invalid Bible API key.")
        if resp.status_code == 404:
            raise ReadwiseAPIError(f"{book_id} chapter {chapter} not found in {translation}.")
        if resp.status_code >= 400:
            raise ReadwiseAPIError(f"Bible API error (HTTP {resp.status_code}).")
        return resp.json()

    return cached_fetch(key, _fetch, BIBLE_CACHE_TTL)
