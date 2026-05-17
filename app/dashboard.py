from flask import Blueprint, render_template

dashboard_bp = Blueprint("dashboard_bp", __name__)


@dashboard_bp.route("/")
def index() -> str:
    return render_template("dashboard.html")
