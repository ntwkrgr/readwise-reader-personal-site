from flask import Blueprint

bible_bp = Blueprint("bible_bp", __name__, url_prefix="/bible")

from app.bible import routes  # noqa: E402, F401
