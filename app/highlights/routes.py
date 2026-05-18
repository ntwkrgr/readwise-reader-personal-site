from flask import render_template, request

from app.highlights import highlights_bp
from app.highlights.api import fetch_books, fetch_daily_review, fetch_highlights
from app.shared import ReadwiseAPIError


def _review_url(data: dict) -> str | None:
    review_url = data.get("review_url")
    if review_url:
        return review_url

    review_id = data.get("review_id")
    if review_id:
        return f"https://readwise.io/reviews/{review_id}"

    return None


@highlights_bp.route("/")
def daily_review():
    try:
        data = fetch_daily_review()
        books_data = fetch_books()
    except ReadwiseAPIError as e:
        return render_template("error.html", message=str(e), retry_url=request.url)

    books = {b["id"]: b for b in books_data.get("results", [])}
    highlights = data.get("highlights", [])

    return render_template(
        "highlights/review.html",
        highlights=highlights,
        books=books,
        review_url=_review_url(data),
    )


@highlights_bp.route("/review")
def daily_review_legacy():
    return daily_review()


@highlights_bp.route("/all")
def highlights_list():
    page = request.args.get("page", 1, type=int) or 1
    try:
        data = fetch_highlights(page=page)
        books_data = fetch_books()
    except ReadwiseAPIError as e:
        return render_template("error.html", message=str(e), retry_url=request.url)

    books = {b["id"]: b for b in books_data.get("results", [])}
    highlights = data.get("results", [])

    return render_template(
        "highlights/list.html",
        highlights=highlights,
        books=books,
        page=page,
        next_page=page + 1 if data.get("next") else None,
        prev_page=page - 1 if page > 1 else None,
        count=data.get("count", 0),
    )
