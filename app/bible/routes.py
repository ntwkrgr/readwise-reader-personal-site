from flask import make_response, redirect, render_template, request, url_for

from app.bible import bible_bp
from app.bible.api import TRANSLATION_IDS
from app.bible.api import fetch_bible_chapter
from app.bible.api import is_available as bible_api_available
from app.bible.web_data import chapter_count, get_books, get_chapter
from app.shared import ReadwiseAPIError

BIBLE_POSITION_COOKIE = "bible_last"


def _all_translations() -> list[str]:
    translations = ["WEB"]
    if bible_api_available():
        translations.extend(TRANSLATION_IDS.keys())
    return translations


@bible_bp.route("/")
def navigator() -> str:
    last = request.cookies.get(BIBLE_POSITION_COOKIE, "")
    if last and not request.args:
        parts = last.split("/")
        if len(parts) == 3:
            translation, book_id, raw_chapter = parts
            try:
                chapter_num = int(raw_chapter)
                return redirect(url_for(
                    "bible_bp.read_chapter",
                    translation=translation,
                    book_id=book_id,
                    chapter_num=chapter_num,
                ))
            except ValueError:
                pass

    books = get_books()
    selected_translation = request.args.get("translation", "WEB")
    selected_book = request.args.get("book", books[0]["id"] if books else "GEN")
    total_chapters = chapter_count(selected_book)
    selected_chapter = request.args.get("chapter", "1")
    try:
        selected_chapter_num = int(selected_chapter)
    except ValueError:
        selected_chapter_num = 1
    selected_chapter_num = min(max(selected_chapter_num, 1), total_chapters or 1)
    book_chapter_counts = {b["id"]: b["chapter_count"] for b in books}
    return render_template(
        "bible/navigator.html",
        translations=_all_translations(),
        books=books,
        selected_translation=selected_translation,
        selected_book=selected_book,
        selected_chapter=selected_chapter_num,
        chapters=list(range(1, total_chapters + 1)),
        book_chapter_counts=book_chapter_counts,
    )


@bible_bp.route("/<translation>/<book_id>/<int:chapter_num>")
def read_chapter(translation: str, book_id: str, chapter_num: int) -> str:
    verses = None
    fums_url = None
    content_html = None
    books = get_books()
    book_name = next((b["name"] for b in books if b["id"] == book_id), book_id)
    total_chapters = chapter_count(book_id)
    book_chapter_counts = {b["id"]: b["chapter_count"] for b in books}

    if translation == "WEB":
        verses = get_chapter(book_id, chapter_num)
        if verses is None:
            return render_template(
                "error.html",
                message=f"{book_name} chapter {chapter_num} not found.",
                retry_url=url_for("bible_bp.navigator"),
            ), 404
    else:
        try:
            data = fetch_bible_chapter(translation, book_id, chapter_num)
            content_html = data.get("data", {}).get("content", "")
            fums_url = data.get("data", {}).get("fums_url")
        except ReadwiseAPIError as e:
            return render_template(
                "error.html",
                message=str(e),
                retry_url=url_for("bible_bp.navigator"),
            ), 502

    resp = make_response(render_template(
        "bible/chapter.html",
        translation=translation,
        book_id=book_id,
        book_name=book_name,
        chapter_num=chapter_num,
        verses=verses,
        content_html=content_html,
        fums_url=fums_url,
        prev_chapter=chapter_num - 1 if chapter_num > 1 else None,
        next_chapter=chapter_num + 1 if chapter_num < total_chapters else None,
        books=books,
        translations=_all_translations(),
        chapters=list(range(1, total_chapters + 1)),
        book_chapter_counts=book_chapter_counts,
    ))
    resp.set_cookie(
        BIBLE_POSITION_COOKIE,
        f"{translation}/{book_id}/{chapter_num}",
        max_age=365 * 24 * 60 * 60,
    )
    return resp
