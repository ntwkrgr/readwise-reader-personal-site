"""Tests for notebook blueprint."""

from unittest.mock import patch

import pytest

from app import create_app
from app.notebook import storage


@pytest.fixture
def notes_dir(tmp_path):
    d = tmp_path / "notes"
    d.mkdir()
    with patch.object(storage, "NOTES_DIR", str(d)):
        yield d


@pytest.fixture
def client(notes_dir):
    app = create_app({"TESTING": True})
    with app.test_client() as c:
        yield c


# --- storage.save_note ---


def test_save_note_journal_filename(notes_dir):
    filename = storage.save_note("journal", "Hello there")
    assert filename.startswith("journal-")
    assert filename.endswith(".txt")
    assert storage.FILENAME_RE.fullmatch(filename)


def test_save_note_thing_filename(notes_dir):
    filename = storage.save_note("thing", "Buy milk")
    assert filename.startswith("thing-")
    assert storage.FILENAME_RE.fullmatch(filename)


def test_save_note_writes_content_verbatim(notes_dir):
    filename = storage.save_note("journal", "Line one\nLine two")
    written = (notes_dir / filename).read_text()
    assert written == "Line one\nLine two\n"


def test_save_note_normalizes_crlf(notes_dir):
    filename = storage.save_note("journal", "Line one\r\nLine two\r\n")
    written = (notes_dir / filename).read_text()
    assert "\r" not in written
    assert written == "Line one\nLine two\n"


def test_save_note_invalid_kind_raises(notes_dir):
    with pytest.raises(storage.NotebookError):
        storage.save_note("bogus", "text")


def test_save_note_creates_dir_if_missing(tmp_path):
    missing = tmp_path / "does" / "not" / "exist"
    with patch.object(storage, "NOTES_DIR", str(missing)):
        filename = storage.save_note("journal", "Hello")
        assert (missing / filename).exists()


def test_save_note_collision_produces_distinct_files(notes_dir):
    fixed_time = storage.datetime(2026, 8, 30, 14, 32, 5, tzinfo=storage._notes_tzinfo())

    class _FrozenDateTime(storage.datetime):
        _calls = [0]

        @classmethod
        def now(cls, tz=None):
            cls._calls[0] += 1
            return fixed_time if cls._calls[0] == 1 else fixed_time.replace(second=fixed_time.second + 1)

    with patch.object(storage, "datetime", _FrozenDateTime):
        first = storage.save_note("journal", "First")
        second = storage.save_note("journal", "Second")

    assert first != second
    assert (notes_dir / first).read_text() == "First\n"
    assert (notes_dir / second).read_text() == "Second\n"


# --- storage.list_notes ---


def test_list_notes_newest_first(notes_dir):
    (notes_dir / "journal-20260101-120000.txt").write_text("old\n")
    (notes_dir / "thing-20260830-090000.txt").write_text("newer\n")
    (notes_dir / "journal-20260830-143205.txt").write_text("newest\n")

    notes = storage.list_notes()

    assert [n.filename for n in notes] == [
        "journal-20260830-143205.txt",
        "thing-20260830-090000.txt",
        "journal-20260101-120000.txt",
    ]


def test_list_notes_ignores_unrelated_files(notes_dir):
    (notes_dir / "journal-20260830-143205.txt").write_text("note\n")
    (notes_dir / "README.md").write_text("not a note\n")
    (notes_dir / ".tmp-abc123").write_text("partial\n")

    notes = storage.list_notes()

    assert [n.filename for n in notes] == ["journal-20260830-143205.txt"]


def test_list_notes_empty_dir(notes_dir):
    assert storage.list_notes() == []


def test_list_notes_preview_is_truncated_and_collapsed(notes_dir):
    long_text = "word " * 100
    (notes_dir / "journal-20260830-143205.txt").write_text(long_text)

    notes = storage.list_notes()

    assert len(notes) == 1
    assert len(notes[0].preview) <= storage.PREVIEW_CHARS + 1  # allow ellipsis
    assert "\n" not in notes[0].preview


# --- storage.read_note ---


def test_read_note_round_trips(notes_dir):
    filename = storage.save_note("thing", "Buy milk\nBuy eggs")
    note = storage.read_note(filename)
    assert note.text == "Buy milk\nBuy eggs\n"
    assert note.kind == "thing"
    assert note.filename == filename


def test_read_note_rejects_path_traversal(notes_dir):
    with pytest.raises(storage.NotebookError):
        storage.read_note("../../etc/passwd")


def test_read_note_rejects_invalid_filename(notes_dir):
    with pytest.raises(storage.NotebookError):
        storage.read_note("evil.txt")


def test_read_note_missing_file_raises(notes_dir):
    with pytest.raises(storage.NotebookError):
        storage.read_note("journal-20260830-143205.txt")


# --- routes: GET /notebook/ ---


def test_entry_page_renders(client):
    resp = client.get("/notebook/")
    assert resp.status_code == 200
    assert b"Journal" in resp.data
    assert b"Thing" in resp.data
    assert b"<textarea" in resp.data


def test_entry_page_kind_query_param_thing_checked(client):
    resp = client.get("/notebook/?kind=thing")
    html = resp.data.decode()
    # the "thing" radio should be checked, not the journal one
    thing_pos = html.index('value="thing"')
    journal_pos = html.index('value="journal"')
    assert "checked" in html[thing_pos:thing_pos + 60]
    assert "checked" not in html[journal_pos:journal_pos + 60]


def test_entry_page_invalid_kind_falls_back_to_journal(client):
    resp = client.get("/notebook/?kind=bogus")
    html = resp.data.decode()
    journal_pos = html.index('value="journal"')
    assert "checked" in html[journal_pos:journal_pos + 60]


# --- routes: POST /notebook/ ---


def test_post_saves_file_and_redirects(client, notes_dir):
    resp = client.post("/notebook/", data={"kind": "journal", "text": "Hello world"})
    assert resp.status_code == 302
    files = list(notes_dir.iterdir())
    assert len(files) == 1
    assert files[0].name.startswith("journal-")


def test_post_flash_shows_filename(client, notes_dir):
    resp = client.post(
        "/notebook/", data={"kind": "journal", "text": "Hello world"}, follow_redirects=True
    )
    filename = next(notes_dir.iterdir()).name
    assert filename.encode() in resp.data
    assert b"Saved as" in resp.data


def test_post_blank_text_does_not_save(client, notes_dir):
    resp = client.post("/notebook/", data={"kind": "journal", "text": "   "}, follow_redirects=True)
    assert resp.status_code == 200
    assert list(notes_dir.iterdir()) == []
    assert b"Write something" in resp.data


def test_post_thing_kind_saves_thing_filename(client, notes_dir):
    client.post("/notebook/", data={"kind": "thing", "text": "Buy milk"})
    files = list(notes_dir.iterdir())
    assert len(files) == 1
    assert files[0].name.startswith("thing-")


# --- routes: GET /notebook/notes ---


def test_notes_list_renders_newest_first(client, notes_dir):
    (notes_dir / "journal-20260101-120000.txt").write_text("old note\n")
    (notes_dir / "thing-20260830-090000.txt").write_text("newer note\n")

    resp = client.get("/notebook/notes")

    assert resp.status_code == 200
    html = resp.data.decode()
    assert html.index("thing-20260830-090000.txt") < html.index("journal-20260101-120000.txt")


def test_notes_list_empty_state(client):
    resp = client.get("/notebook/notes")
    assert resp.status_code == 200
    assert b"empty" in resp.data.lower() or b"No notes" in resp.data


# --- routes: GET /notebook/notes/<filename> ---


def test_note_detail_renders_body(client, notes_dir):
    (notes_dir / "journal-20260830-143205.txt").write_text("My full journal text\n")

    resp = client.get("/notebook/notes/journal-20260830-143205.txt")

    assert resp.status_code == 200
    assert b"My full journal text" in resp.data


def test_note_detail_rejects_path_traversal(client):
    resp = client.get("/notebook/notes/..%2f..%2fetc%2fpasswd")
    assert resp.status_code in (200, 404)
    assert b"root:" not in resp.data


def test_note_detail_missing_file_shows_error(client):
    resp = client.get("/notebook/notes/journal-20260830-143205.txt")
    assert resp.status_code == 200
    assert b"Something went wrong" in resp.data


# --- dashboard integration ---


def test_dashboard_includes_notebook_link(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Notebook" in resp.data
    assert b'href="/notebook/"' in resp.data


def test_dashboard_settings_link_still_last(client):
    resp = client.get("/")
    html = resp.data.decode()
    assert 'class="dashboard-link dashboard-settings-link"' in html
    assert "margin-top: auto" in html
