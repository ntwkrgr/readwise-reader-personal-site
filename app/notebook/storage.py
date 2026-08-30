"""Disk storage for Notebook entries.

Notes are written as plain UTF-8 .txt files named ``<kind>-<timestamp>.txt``.
The filename contract is load-bearing: external automations outside this
codebase watch NOTES_DIR and classify files by their prefix, so the naming
rules here must not change casually.
"""

import os
import re
import uuid
from datetime import datetime, timedelta
from typing import NamedTuple

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover - zoneinfo ships with Python 3.9+
    ZoneInfo = None
    ZoneInfoNotFoundError = Exception

_APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
NOTES_DIR = os.environ.get("NOTES_DIR", os.path.join(_APP_DIR, "notes"))
NOTES_TZ = os.environ.get("NOTES_TZ", "America/Chicago")

VALID_KINDS = ("journal", "thing")
DEFAULT_KIND = "journal"
FILENAME_RE = re.compile(r"^(journal|thing)-(\d{8})-(\d{6})\.txt$")
PREVIEW_CHARS = 120
MAX_COLLISION_ATTEMPTS = 60


class NotebookError(Exception):
    """Raised for any Notebook storage failure that should be shown to the user."""


class Note(NamedTuple):
    filename: str
    kind: str
    created_at: datetime
    preview: str
    text: str


def _notes_tzinfo():
    """Return the configured Notebook timezone, or None to fall back to local time."""
    if ZoneInfo is None:
        return None
    try:
        return ZoneInfo(NOTES_TZ)
    except ZoneInfoNotFoundError:
        return None


def _generate_filename(kind: str, when: datetime) -> str:
    return f"{kind}-{when.strftime('%Y%m%d-%H%M%S')}.txt"


def _parse_filename(filename: str) -> tuple[str, datetime] | None:
    match = FILENAME_RE.fullmatch(filename)
    if not match:
        return None
    kind, date_part, time_part = match.groups()
    try:
        created_at = datetime.strptime(f"{date_part}{time_part}", "%Y%m%d%H%M%S")
    except ValueError:
        return None
    return kind, created_at


def _preview_of(text: str) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= PREVIEW_CHARS:
        return collapsed
    return collapsed[:PREVIEW_CHARS].rstrip() + "…"


def save_note(kind: str, text: str) -> str:
    """Write a note to disk and return its filename."""
    if kind not in VALID_KINDS:
        raise NotebookError(f"Unknown note type: {kind!r}")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    content = normalized + "\n"

    try:
        os.makedirs(NOTES_DIR, exist_ok=True)
    except OSError as e:
        raise NotebookError("Could not create the notes folder.") from e

    when = datetime.now(_notes_tzinfo())
    tmp_path = os.path.join(NOTES_DIR, f".tmp-{uuid.uuid4().hex}")

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)

        for attempt in range(MAX_COLLISION_ATTEMPTS):
            candidate = when if attempt == 0 else when + timedelta(seconds=attempt)
            filename = _generate_filename(kind, candidate)
            final_path = os.path.join(NOTES_DIR, filename)
            try:
                os.link(tmp_path, final_path)
                return filename
            except FileExistsError:
                continue

        raise NotebookError("Could not save the note — too many notes saved this second.")
    except OSError as e:
        raise NotebookError("Could not save the note — check the notes folder is writable.") from e
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def list_notes() -> list[Note]:
    """Return every note, newest first, without loading full text."""
    try:
        filenames = os.listdir(NOTES_DIR)
    except FileNotFoundError:
        return []
    except OSError as e:
        raise NotebookError("Could not read the notes folder.") from e

    notes = []
    for filename in filenames:
        parsed = _parse_filename(filename)
        if parsed is None:
            continue
        kind, created_at = parsed
        path = os.path.join(NOTES_DIR, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        notes.append(
            Note(filename=filename, kind=kind, created_at=created_at, preview=_preview_of(text), text="")
        )

    notes.sort(key=lambda n: n.created_at, reverse=True)
    return notes


def read_note(filename: str) -> Note:
    """Return one note's full text. Rejects anything not shaped like a note filename."""
    parsed = _parse_filename(filename)
    if parsed is None:
        raise NotebookError("That note doesn't exist.")
    kind, created_at = parsed

    notes_root = os.path.realpath(NOTES_DIR)
    path = os.path.realpath(os.path.join(NOTES_DIR, filename))
    if path != os.path.join(notes_root, filename):
        raise NotebookError("That note doesn't exist.")

    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError as e:
        raise NotebookError("That note doesn't exist.") from e
    except OSError as e:
        raise NotebookError("Could not read that note.") from e

    return Note(filename=filename, kind=kind, created_at=created_at, preview=_preview_of(text), text=text)
