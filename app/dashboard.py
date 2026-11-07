from flask import Blueprint, render_template

from app.weather import fetch_weather

dashboard_bp = Blueprint("dashboard_bp", __name__)


@dashboard_bp.route("/")
def index() -> str:
    """Render the home page: weather hero card (or its fallback) above the section cards."""
    return render_template("dashboard.html", weather=fetch_weather())
