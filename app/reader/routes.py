import random

from typing import Any

from flask import flash, redirect, render_template, request, url_for

from app.cache import can_refresh, mark_refresh, cache_age_seconds, invalidate_list_cache
from app.settings import SORT_COOKIE, VALID_SORTS
from app.shared import ReadwiseAPIError, sanitize_html

from . import reader_bp
from .api import archive_article, fetch_article, fetch_article_list, save_highlight_to_readwise

VALID_LOCATIONS = {"all", "later", "new"}


def _sort_articles(articles: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    if sort == "random":
        out = list(articles)
        random.shuffle(out)
        return out

    def sort_key(a: dict[str, Any]) -> str:
        return a.get("saved_at") or a.get("created_at") or ""

    return sorted(articles, key=sort_key, reverse=(sort == "newest"))


@reader_bp.route("/")
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
        if can_refresh():
            invalidate_list_cache()
            mark_refresh()
        else:
            flash("List was refreshed recently — try again in a moment.")

    try:
        data = fetch_article_list(location=location, page_cursor=page_cursor, tag=tag)
    except ReadwiseAPIError as e:
        return render_template("error.html", message=str(e), retry_url=request.url)

    articles = _sort_articles(data["results"], sort)

    return render_template(
        "reader/list.html",
        articles=articles,
        next_cursor=data["nextPageCursor"],
        current_location=location,
        current_tag=tag,
        current_sort=sort,
        count=data["count"],
        cache_age_seconds=cache_age_seconds(),
    )


@reader_bp.route("/read/<doc_id>")
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
        "reader/read.html",
        article=article,
        html_content=html_content,
        has_content=has_content,
    )


@reader_bp.route("/read/<doc_id>/note", methods=["GET", "POST"])
def add_note(doc_id: str):
    if request.method == "POST":
        text = (request.form.get("text") or "").strip()
        if not text:
            flash("Enter some text for the note.")
            return redirect(url_for("reader_bp.add_note", doc_id=doc_id))
        try:
            article = fetch_article(doc_id)
        except ReadwiseAPIError as e:
            return render_template(
                "error.html",
                message=str(e),
                retry_url=url_for("reader_bp.read_article", doc_id=doc_id),
            )
        try:
            save_highlight_to_readwise(article, text)
        except ReadwiseAPIError as e:
            return render_template(
                "error.html",
                message=str(e),
                retry_url=url_for("reader_bp.add_note", doc_id=doc_id),
            )
        flash("Note saved to Readwise.")
        return redirect(url_for("reader_bp.read_article", doc_id=doc_id))
    try:
        article = fetch_article(doc_id)
    except ReadwiseAPIError as e:
        return render_template(
            "error.html", message=str(e), retry_url=url_for("reader_bp.article_list")
        )
    return render_template("reader/note.html", article=article)


@reader_bp.route("/archive/<doc_id>", methods=["POST"])
def do_archive(doc_id: str):
    try:
        archive_article(doc_id)
    except ReadwiseAPIError as e:
        return render_template(
            "error.html", message=str(e), retry_url=url_for("reader_bp.article_list")
        )

    flash("Article archived.")
    return redirect(url_for("reader_bp.article_list"))


@reader_bp.route("/tags")
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
        "reader/tags.html",
        tags=sorted(tag_names),
        current_location=location,
    )
