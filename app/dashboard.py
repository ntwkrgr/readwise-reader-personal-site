from flask import Blueprint, redirect, url_for

dashboard_bp = Blueprint("dashboard_bp", __name__)


@dashboard_bp.route("/")
def dashboard():
    return redirect(url_for("reader_bp.article_list"))
