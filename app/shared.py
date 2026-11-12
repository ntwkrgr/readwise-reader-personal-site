import html
import os
import re
import time

from html.entities import html5
from typing import Any

from bs4 import BeautifulSoup

import requests as http_requests

READWISE_TOKEN = os.environ.get("READWISE_TOKEN", "")
READWISE_API_BASE = "https://readwise.io/api/v3"

# A named HTML entity such as "&amp;", or Readwise's title-cased "&Amp;"
_NAMED_ENTITY = re.compile(r"&([A-Za-z]+);")


def decode_entities(value: str | None) -> str | None:
    """Decode HTML entities Readwise leaves in plain-text fields ("Let&#39;s" -> "Let's").

    Readwise title-cases some imported book titles, turning "&amp;" into "&Amp;", so entity
    names Python doesn't recognize as written are lower-cased before decoding.
    """
    if not value:
        return value
    # Lower-case unrecognized entity names (&Amp; -> &amp;); case-sensitive ones like &Eacute; stay
    value = _NAMED_ENTITY.sub(lambda m: m.group(0) if m.group(1) + ";" in html5 else m.group(0).lower(), value)
    return html.unescape(value)


class ReadwiseAPIError(Exception):
    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


def api_headers() -> dict[str, str]:
    return {
        "Authorization": f"Token {READWISE_TOKEN}",
        "Content-Type": "application/json",
    }


def handle_api_response(resp: http_requests.Response) -> dict[str, Any]:
    if resp.status_code == 401:
        raise ReadwiseAPIError("Invalid API token — check your .env file.")
    if resp.status_code == 429:
        retry = resp.headers.get("Retry-After")
        retry_sec = int(retry) if retry else None
        raise ReadwiseAPIError(
            "Too many requests — wait a moment and tap to retry.",
            retry_after=retry_sec,
        )
    if resp.status_code >= 400:
        raise ReadwiseAPIError(f"Readwise returned an error (HTTP {resp.status_code}).")
    return resp.json()


def api_get(url: str, params: dict | None = None) -> dict[str, Any]:
    """GET with a single transparent retry on 429."""
    for attempt in range(2):
        try:
            resp = http_requests.get(url, headers=api_headers(), params=params, timeout=15)
        except http_requests.RequestException:
            raise ReadwiseAPIError("Could not reach Readwise — check your network connection.")
        if resp.status_code == 429 and attempt == 0:
            retry_after = resp.headers.get("Retry-After")
            wait = min(int(retry_after) if retry_after else 5, 15)
            time.sleep(wait)
            continue
        return handle_api_response(resp)
    raise ReadwiseAPIError("Too many requests — wait a moment and tap to retry.")


STRIP_TAGS = {"img", "picture", "figure", "svg", "video", "audio", "iframe", "source"}


def sanitize_html(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup.find_all(STRIP_TAGS):
        tag.decompose()
    return str(soup)
