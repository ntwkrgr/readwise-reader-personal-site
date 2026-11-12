from flask import Blueprint, render_template

from app.highlights.api import fetch_highlight_of_the_day
from app.weather import fetch_weather

dashboard_bp = Blueprint("dashboard_bp", __name__)


@dashboard_bp.route("/")
def index() -> str:
    """Render the home page: weather hero card, section cards, and the highlight of the day."""
    return render_template(
        "dashboard.html",
        weather=fetch_weather(),
        highlight=fetch_highlight_of_the_day(),
    )
