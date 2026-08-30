from flask import flash, redirect, render_template, request, url_for

from app.notebook import notebook_bp
from app.notebook.storage import DEFAULT_KIND, VALID_KINDS, NotebookError, list_notes, read_note, save_note


@notebook_bp.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        kind = request.form.get("kind", DEFAULT_KIND)
        if kind not in VALID_KINDS:
            kind = DEFAULT_KIND
        text = (request.form.get("text") or "").strip()

        if not text:
            flash("Write something before saving.")
            return redirect(url_for("notebook_bp.index", kind=kind))

        try:
            filename = save_note(kind, text)
        except NotebookError as e:
            return render_template(
                "error.html", message=str(e), retry_url=url_for("notebook_bp.index")
            )

        flash(f"Saved as {filename}")
        return redirect(url_for("notebook_bp.index", kind=kind))

    kind = request.args.get("kind", DEFAULT_KIND)
    if kind not in VALID_KINDS:
        kind = DEFAULT_KIND
    return render_template("notebook/entry.html", kind=kind)


@notebook_bp.route("/notes")
def notes_list():
    try:
        notes = list_notes()
    except NotebookError as e:
        return render_template(
            "error.html", message=str(e), retry_url=url_for("notebook_bp.notes_list")
        )
    return render_template("notebook/list.html", notes=notes)


@notebook_bp.route("/notes/<filename>")
def note_detail(filename: str):
    try:
        note = read_note(filename)
    except NotebookError as e:
        return render_template(
            "error.html", message=str(e), retry_url=url_for("notebook_bp.notes_list")
        )
    return render_template("notebook/read.html", note=note)
