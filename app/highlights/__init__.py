from flask import Blueprint

highlights_bp = Blueprint("highlights_bp", __name__, url_prefix="/highlights")

from app.highlights import routes  # noqa: E402, F401
