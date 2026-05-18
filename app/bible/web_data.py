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
CANONICAL_CHAPTER_COUNTS: dict[str, int] = {
    "GEN": 50,
    "EXO": 40,
    "LEV": 27,
    "NUM": 36,
    "DEU": 34,
    "JOS": 24,
    "JDG": 21,
    "RUT": 4,
    "1SA": 31,
    "2SA": 24,
    "1KI": 22,
    "2KI": 25,
    "1CH": 29,
    "2CH": 36,
    "EZR": 10,
    "NEH": 13,
    "EST": 10,
    "JOB": 42,
    "PSA": 150,
    "PRO": 31,
    "ECC": 12,
    "SNG": 8,
    "ISA": 66,
    "JER": 52,
    "LAM": 5,
    "EZK": 48,
    "DAN": 12,
    "HOS": 14,
    "JOL": 3,
    "AMO": 9,
    "OBA": 1,
    "JON": 4,
    "MIC": 7,
    "NAH": 3,
    "HAB": 3,
    "ZEP": 3,
    "HAG": 2,
    "ZEC": 14,
    "MAL": 4,
    "MAT": 28,
    "MRK": 16,
    "LUK": 24,
    "JHN": 21,
    "ACT": 28,
    "ROM": 16,
    "1CO": 16,
    "2CO": 13,
    "GAL": 6,
    "EPH": 6,
    "PHP": 4,
    "COL": 4,
    "1TH": 5,
    "2TH": 3,
    "1TI": 6,
    "2TI": 4,
    "TIT": 3,
    "PHM": 1,
    "HEB": 13,
    "JAS": 5,
    "1PE": 5,
    "2PE": 3,
    "1JN": 5,
    "2JN": 1,
    "3JN": 1,
    "JUD": 1,
    "REV": 22,
}

for _b in _raw.get("books", []):
    _BOOKS.append({
        "id": _b["id"],
        "name": _b["name"],
        "chapter_count": CANONICAL_CHAPTER_COUNTS.get(_b["id"], len(_b["chapters"])),
    })
    for _ch in _b.get("chapters", []):
        _CHAPTER_INDEX[(_b["id"], _ch["number"])] = _ch.get("verses", [])


def get_books() -> list[dict[str, Any]]:
    return _BOOKS


def get_chapter(book_id: str, chapter_number: int) -> list[dict[str, Any]] | None:
    return _CHAPTER_INDEX.get((book_id, chapter_number))


def chapter_count(book_id: str) -> int:
    b = next((b for b in _BOOKS if b["id"] == book_id), None)
    return b["chapter_count"] if b else 0
