from flask import Blueprint

notebook_bp = Blueprint("notebook_bp", __name__, url_prefix="/notebook")

from app.notebook import routes  # noqa: E402, F401
