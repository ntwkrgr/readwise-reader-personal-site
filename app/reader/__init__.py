from flask import Blueprint

reader_bp = Blueprint("reader_bp", __name__, url_prefix="/reader")

from . import routes  # noqa: E402,F401
