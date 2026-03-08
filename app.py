import os
import uuid

from typing import Any

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

VALID_LOCATIONS = {"later", "new", "archive", "feed"}

# --- Cache ---

_list_cache: dict[tuple[str, str | None, str | None], dict[str, Any]] = {}
_article_cache: dict[str, dict[str, Any]] = {}


def invalidate_list_cache() -> None:
    _list_cache.clear()


def invalidate_article_cache(doc_id: str) -> None:
    _article_cache.pop(doc_id, None)


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


def fetch_article_list(
    location: str = "later",
    page_cursor: str | None = None,
    tag: str | None = None,
) -> dict[str, Any]:
    cache_key = (location, page_cursor, tag)
    if cache_key in _list_cache:
        return _list_cache[cache_key]

    params: dict[str, str | int] = {
        "location": location,
        "category": "article",
        "limit": ARTICLES_PER_PAGE,
    }
    if page_cursor:
        params["pageCursor"] = page_cursor
    if tag:
        params["tag"] = tag

    try:
        resp = http_requests.get(
            f"{READWISE_API_BASE}/list/",
            headers=_api_headers(),
            params=params,
            timeout=15,
        )
    except http_requests.RequestException:
        raise ReadwiseAPIError("Could not reach Readwise — check your network connection.")

    data = _handle_api_response(resp)

    results = [r for r in data.get("results", []) if r.get("parent_id") is None]
    result = {
        "results": results,
        "nextPageCursor": data.get("nextPageCursor"),
        "count": data.get("count", 0),
    }
    _list_cache[cache_key] = result
    return result


def fetch_article(doc_id: str) -> dict[str, Any]:
    if doc_id in _article_cache:
        return _article_cache[doc_id]

    params: dict[str, str] = {"id": doc_id, "withHtmlContent": "true"}
    try:
        resp = http_requests.get(
            f"{READWISE_API_BASE}/list/",
            headers=_api_headers(),
            params=params,
            timeout=15,
        )
    except http_requests.RequestException:
        raise ReadwiseAPIError("Could not reach Readwise — check your network connection.")

    data = _handle_api_response(resp)
    results = data.get("results", [])
    if not results:
        raise ReadwiseAPIError("Article not found.")

    article = results[0]
    _article_cache[doc_id] = article
    return article


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
VALID_TEXT_SIZES = {"small", "medium", "large"}
VALID_TEXT_WEIGHTS = {"normal", "bold"}


@app.context_processor
def inject_display_prefs():
    size = request.cookies.get(TEXT_SIZE_COOKIE, "medium")
    weight = request.cookies.get(TEXT_WEIGHT_COOKIE, "normal")
    if size not in VALID_TEXT_SIZES:
        size = "medium"
    if weight not in VALID_TEXT_WEIGHTS:
        weight = "normal"
    return {"text_size": size, "text_weight": weight}


# --- Routes ---


@app.route("/")
def article_list():
    location = request.args.get("location", "later")
    if location not in VALID_LOCATIONS:
        location = "later"
    page_cursor = request.args.get("cursor")
    refresh = request.args.get("refresh")
    tag = request.args.get("tag")

    if refresh:
        invalidate_list_cache()

    try:
        data = fetch_article_list(location=location, page_cursor=page_cursor, tag=tag)
    except ReadwiseAPIError as e:
        return render_template("error.html", message=str(e), retry_url=request.url)

    return render_template(
        "list.html",
        articles=data["results"],
        next_cursor=data["nextPageCursor"],
        current_location=location,
        current_tag=tag,
        count=data["count"],
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
        if size not in VALID_TEXT_SIZES:
            size = "medium"
        if weight not in VALID_TEXT_WEIGHTS:
            weight = "normal"
        resp = make_response(redirect(request.referrer or url_for("article_list")))
        resp.set_cookie(TEXT_SIZE_COOKIE, size, max_age=31536000)
        resp.set_cookie(TEXT_WEIGHT_COOKIE, weight, max_age=31536000)
        return resp
    return render_template("settings.html")


@app.route("/tags")
def tag_picker():
    location = request.args.get("location", "later")
    if location not in VALID_LOCATIONS:
        location = "later"
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


if __name__ == "__main__":
    if not READWISE_TOKEN:
        print("WARNING: READWISE_TOKEN not set. Create a .env file — see .env.example")
    port = int(os.environ.get("PORT", 5555))
    app.run(host="0.0.0.0", port=port, debug=True)
