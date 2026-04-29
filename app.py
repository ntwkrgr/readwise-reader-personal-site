import os
import time
import uuid
import random
import threading

from typing import Any

import diskcache
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, flash, make_response, redirect, render_template, request, url_for

import requests as http_requests

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", uuid.uuid4().hex)

READWISE_TOKEN = os.environ.get("READWISE_TOKEN", "")
READWISE_API_BASE = "https://readwise.io/api/v3"
ARTICLES_PER_PAGE = 20

VALID_LOCATIONS = {"all", "later", "new"}
VALID_SORTS = {"newest", "oldest", "random"}

_APP_DIR = os.path.abspath(os.path.dirname(__file__))
CACHE_DIR = os.environ.get("CACHE_DIR", os.path.join(_APP_DIR, ".cache"))
LIST_CACHE_TTL = int(os.environ.get("LIST_CACHE_TTL", 1200))   # 20 minutes
ARTICLE_CACHE_TTL = int(os.environ.get("ARTICLE_CACHE_TTL", 3600))  # 60 minutes
REFRESH_COOLDOWN = 120  # 2 minutes

_MISSING = object()
_cache = diskcache.Cache(CACHE_DIR)


# --- Cache helpers ---

def _list_version() -> int:
    return _cache.get("list_version", default=0)


def _list_key(location: str, page_cursor: str | None, tag: str | None) -> str:
    return f"list:v{_list_version()}:{location}:{page_cursor or ''}:{tag or ''}"


def _article_key(doc_id: str) -> str:
    return f"article:{doc_id}"


def _cached_fetch(key: str, fetch_fn, ttl: int) -> Any:
    """Double-checked lock: check → lock → check → fetch → store.

    expire=30 on the Lock auto-releases it if the holder dies mid-operation,
    preventing permanent deadlocks across gunicorn workers.
    """
    result = _cache.get(key, default=_MISSING)
    if result is not _MISSING:
        return result
    with diskcache.Lock(_cache, f"lock:{key}", expire=30):
        result = _cache.get(key, default=_MISSING)
        if result is not _MISSING:
            return result
        result = fetch_fn()
        _cache.set(key, result, expire=ttl)
        return result


def invalidate_list_cache() -> None:
    _cache.incr("list_version", default=0)


def invalidate_article_cache(doc_id: str) -> None:
    _cache.delete(_article_key(doc_id))


def _can_refresh() -> bool:
    last = _cache.get("last_refresh")
    return last is None or (time.time() - last) >= REFRESH_COOLDOWN


def _mark_refresh() -> None:
    _cache.set("last_refresh", time.time())


def cache_age_seconds() -> int | None:
    last = _cache.get("last_refresh")
    return int(time.time() - last) if last is not None else None


# --- Readwise API helpers ---


class ReadwiseAPIError(Exception):
    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


def _api_headers() -> dict[str, str]:
    return {
        "Authorization": f"Token {READWISE_TOKEN}",
        "Content-Type": "application/json",
    }


def _handle_api_response(resp: http_requests.Response) -> dict[str, Any]:
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


def _api_get(url: str, params: dict | None = None) -> dict[str, Any]:
    """GET with a single transparent retry on 429."""
    for attempt in range(2):
        try:
            resp = http_requests.get(url, headers=_api_headers(), params=params, timeout=15)
        except http_requests.RequestException:
            raise ReadwiseAPIError("Could not reach Readwise — check your network connection.")
        if resp.status_code == 429 and attempt == 0:
            retry_after = resp.headers.get("Retry-After")
            wait = min(int(retry_after) if retry_after else 5, 15)
            time.sleep(wait)
            continue
        return _handle_api_response(resp)
    raise ReadwiseAPIError("Too many requests — wait a moment and tap to retry.")


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
    data = _api_get(f"{READWISE_API_BASE}/list/", params=params)
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
    return _cached_fetch(
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
    return _cached_fetch(
        key, lambda: _fetch_all_active_articles_from_api(page_cursor, tag), LIST_CACHE_TTL
    )


def _fetch_article_from_api(doc_id: str) -> dict[str, Any]:
    params: dict[str, str] = {"id": doc_id, "withHtmlContent": "true"}
    data = _api_get(f"{READWISE_API_BASE}/list/", params=params)
    results = data.get("results", [])
    if not results:
        raise ReadwiseAPIError("Article not found.")
    article = results[0]
    if not _is_included_new_or_later_item(article):
        raise ReadwiseAPIError("This reader only shows Articles/RSS saved to New or Later.")
    return article


def fetch_article(doc_id: str) -> dict[str, Any]:
    key = _article_key(doc_id)
    return _cached_fetch(key, lambda: _fetch_article_from_api(doc_id), ARTICLE_CACHE_TTL)


def archive_article(doc_id: str) -> None:
    try:
        resp = http_requests.patch(
            f"{READWISE_API_BASE}/update/{doc_id}",
            headers=_api_headers(),
            json={"location": "archive"},
            timeout=15,
        )
    except http_requests.RequestException:
        raise ReadwiseAPIError("Could not reach Readwise — check your network connection.")
    _handle_api_response(resp)
    invalidate_list_cache()
    invalidate_article_cache(doc_id)


# --- HTML sanitization ---

STRIP_TAGS = {"img", "picture", "figure", "svg", "video", "audio", "iframe", "source"}


def sanitize_html(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup.find_all(STRIP_TAGS):
        tag.decompose()
    return str(soup)


# --- Cookie defaults ---

TEXT_SIZE_COOKIE = "readwise_text_size"
TEXT_WEIGHT_COOKIE = "readwise_text_weight"
THEME_COOKIE = "readwise_theme"
TAP_ADVANCE_COOKIE = "readwise_tap_advance"
SORT_COOKIE = "readwise_sort"
VALID_TEXT_SIZES = {"small", "medium", "large"}
VALID_TEXT_WEIGHTS = {"normal", "bold"}
VALID_THEMES = {"light", "dark"}
VALID_TAP_ADVANCE = {"on", "off"}

READWISE_V2_HIGHLIGHTS = "https://readwise.io/api/v2/highlights/"


@app.context_processor
def inject_display_prefs():
    size = request.cookies.get(TEXT_SIZE_COOKIE, "medium")
    weight = request.cookies.get(TEXT_WEIGHT_COOKIE, "normal")
    theme = request.cookies.get(THEME_COOKIE, "light")
    tap_advance = request.cookies.get(TAP_ADVANCE_COOKIE, "off")
    default_sort = request.cookies.get(SORT_COOKIE, "newest")
    if size not in VALID_TEXT_SIZES:
        size = "medium"
    if weight not in VALID_TEXT_WEIGHTS:
        weight = "normal"
    if theme not in VALID_THEMES:
        theme = "light"
    if tap_advance not in VALID_TAP_ADVANCE:
        tap_advance = "off"
    if default_sort not in VALID_SORTS:
        default_sort = "newest"
    return {
        "text_size": size,
        "text_weight": weight,
        "theme": theme,
        "tap_advance_enabled": tap_advance == "on",
        "default_sort": default_sort,
    }


def _sort_articles(articles: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    if sort == "random":
        out = list(articles)
        random.shuffle(out)
        return out

    def sort_key(a: dict[str, Any]) -> str:
        return a.get("saved_at") or a.get("created_at") or ""

    return sorted(articles, key=sort_key, reverse=(sort == "newest"))


# --- Routes ---


@app.route("/")
def article_list():
    location = request.args.get("location", "all")
    if location not in VALID_LOCATIONS:
        location = "all"
    sort = request.cookies.get(SORT_COOKIE, "newest")
    if sort not in VALID_SORTS:
        sort = "newest"
    page_cursor = request.args.get("cursor")
    refresh = request.args.get("refresh")
    tag = request.args.get("tag")

    if refresh:
        if _can_refresh():
            invalidate_list_cache()
            _mark_refresh()
        else:
            flash("List was refreshed recently — try again in a moment.")

    try:
        data = fetch_article_list(location=location, page_cursor=page_cursor, tag=tag)
    except ReadwiseAPIError as e:
        return render_template("error.html", message=str(e), retry_url=request.url)

    articles = _sort_articles(data["results"], sort)

    return render_template(
        "list.html",
        articles=articles,
        next_cursor=data["nextPageCursor"],
        current_location=location,
        current_tag=tag,
        current_sort=sort,
        count=data["count"],
        cache_age_seconds=cache_age_seconds(),
    )


@app.route("/read/<doc_id>")
def read_article(doc_id: str):
    try:
        article = fetch_article(doc_id)
    except ReadwiseAPIError as e:
        return render_template("error.html", message=str(e), retry_url=request.url)

    html_content = article.get("html_content") or ""
    has_content = bool(html_content.strip())
    if has_content:
        html_content = sanitize_html(html_content)

    return render_template(
        "read.html",
        article=article,
        html_content=html_content,
        has_content=has_content,
    )


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
            headers=_api_headers(),
            json=payload,
            timeout=15,
        )
    except http_requests.RequestException:
        raise ReadwiseAPIError("Could not reach Readwise — check your network connection.")
    if resp.status_code == 401:
        raise ReadwiseAPIError("Invalid API token — check your .env file.")
    if resp.status_code >= 400:
        raise ReadwiseAPIError(f"Readwise returned an error (HTTP {resp.status_code}).")


@app.route("/read/<doc_id>/note", methods=["GET", "POST"])
def add_note(doc_id: str):
    if request.method == "POST":
        text = (request.form.get("text") or "").strip()
        if not text:
            flash("Enter some text for the note.")
            return redirect(url_for("add_note", doc_id=doc_id))
        try:
            article = fetch_article(doc_id)
        except ReadwiseAPIError as e:
            return render_template(
                "error.html", message=str(e), retry_url=url_for("read_article", doc_id=doc_id)
            )
        try:
            save_highlight_to_readwise(article, text)
        except ReadwiseAPIError as e:
            return render_template(
                "error.html", message=str(e), retry_url=url_for("add_note", doc_id=doc_id)
            )
        flash("Note saved to Readwise.")
        return redirect(url_for("read_article", doc_id=doc_id))
    try:
        article = fetch_article(doc_id)
    except ReadwiseAPIError as e:
        return render_template(
            "error.html", message=str(e), retry_url=url_for("article_list")
        )
    return render_template("note.html", article=article)


@app.route("/archive/<doc_id>", methods=["POST"])
def do_archive(doc_id: str):
    try:
        archive_article(doc_id)
    except ReadwiseAPIError as e:
        return render_template("error.html", message=str(e), retry_url=url_for("article_list"))

    flash("Article archived.")
    return redirect(url_for("article_list"))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        size = request.form.get("text_size", "medium")
        weight = request.form.get("text_weight", "normal")
        theme = request.form.get("theme", "light")
        tap_advance = request.form.get("tap_advance", "off")
        default_sort = request.form.get("default_sort", "newest")
        if size not in VALID_TEXT_SIZES:
            size = "medium"
        if weight not in VALID_TEXT_WEIGHTS:
            weight = "normal"
        if theme not in VALID_THEMES:
            theme = "light"
        if tap_advance not in VALID_TAP_ADVANCE:
            tap_advance = "off"
        if default_sort not in VALID_SORTS:
            default_sort = "newest"
        resp = make_response(redirect(request.referrer or url_for("article_list")))
        resp.set_cookie(TEXT_SIZE_COOKIE, size, max_age=31536000)
        resp.set_cookie(TEXT_WEIGHT_COOKIE, weight, max_age=31536000)
        resp.set_cookie(THEME_COOKIE, theme, max_age=31536000)
        resp.set_cookie(TAP_ADVANCE_COOKIE, tap_advance, max_age=31536000)
        resp.set_cookie(SORT_COOKIE, default_sort, max_age=31536000)
        return resp
    return render_template("settings.html")


@app.route("/tags")
def tag_picker():
    location = request.args.get("location", "all")
    if location not in VALID_LOCATIONS:
        location = "all"
    try:
        data = fetch_article_list(location=location, page_cursor=None, tag=None)
    except ReadwiseAPIError as e:
        return render_template("error.html", message=str(e), retry_url=request.url)
    tag_names: set[str] = set()
    for article in data["results"]:
        tags = article.get("tags") or {}
        if isinstance(tags, dict):
            tag_names.update(tags.keys())
        elif isinstance(tags, list):
            tag_names.update(tags)
    return render_template(
        "tags.html",
        tags=sorted(tag_names),
        current_location=location,
    )


# --- Startup pre-warm (Phase 3) ---
# Runs in each gunicorn worker after fork. With the diskcache lock, only one
# worker actually hits the API; the others wait and read from cache.

def _prewarm_cache() -> None:
    time.sleep(2)  # Let gunicorn finish worker initialization
    try:
        fetch_article_list(location="later")
        fetch_article_list(location="new")
    except Exception:
        pass  # Best-effort; real errors will surface on first user request


threading.Thread(target=_prewarm_cache, daemon=True).start()


if __name__ == "__main__":
    if not READWISE_TOKEN:
        print("WARNING: READWISE_TOKEN not set. Create a .env file — see .env.example")
    port = int(os.environ.get("PORT", 5555))
    app.run(host="0.0.0.0", port=port, debug=True)
