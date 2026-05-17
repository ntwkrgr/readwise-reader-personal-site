import json
import os
from typing import Any

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "web.json")


def _load() -> dict[str, Any]:
    with open(os.path.normpath(_DATA_PATH)) as f:
        return json.load(f)


try:
    _raw = _load()
except (FileNotFoundError, json.JSONDecodeError) as e:
    raise RuntimeError(f'data/web.json missing or invalid: {e}') from e
_BOOKS: list[dict[str, Any]] = []
_CHAPTER_INDEX: dict[tuple[str, int], list[dict[str, Any]]] = {}

for _b in _raw.get("books", []):
    _BOOKS.append({"id": _b["id"], "name": _b["name"], "chapter_count": len(_b["chapters"])})
    for _ch in _b.get("chapters", []):
        _CHAPTER_INDEX[(_b["id"], _ch["number"])] = _ch.get("verses", [])


def get_books() -> list[dict[str, Any]]:
    return _BOOKS


def get_chapter(book_id: str, chapter_number: int) -> list[dict[str, Any]] | None:
    return _CHAPTER_INDEX.get((book_id, chapter_number))


def chapter_count(book_id: str) -> int:
    b = next((b for b in _BOOKS if b["id"] == book_id), None)
    return b["chapter_count"] if b else 0
