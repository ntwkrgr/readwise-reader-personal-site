from flask import Blueprint, make_response, redirect, render_template, request, url_for

settings_bp = Blueprint("settings_bp", __name__)

TEXT_SIZE_COOKIE = "readwise_text_size"
TEXT_WEIGHT_COOKIE = "readwise_text_weight"
THEME_COOKIE = "readwise_theme"
TAP_ADVANCE_COOKIE = "readwise_tap_advance"
SORT_COOKIE = "readwise_sort"
VALID_TEXT_SIZES = {"small", "medium", "large"}
VALID_TEXT_WEIGHTS = {"normal", "bold"}
VALID_THEMES = {"light", "dark"}
VALID_TAP_ADVANCE = {"on", "off"}
VALID_SORTS = {"newest", "oldest", "random"}


@settings_bp.app_context_processor
def inject_display_prefs():
    size = request.cookies.get(TEXT_SIZE_COOKIE, "medium")
    weight = request.cookies.get(TEXT_WEIGHT_COOKIE, "normal")
    theme = request.cookies.get(THEME_COOKIE, "light")
    tap_advance = request.cookies.get(TAP_ADVANCE_COOKIE, "off")
    default_sort = request.cookies.get(SORT_COOKIE, "newest")
    if size not in VALID_TEXT_SIZES:
        size = "medium"
    if weight not in VALID_TEXT_WEIGHTS:
        weight = "normal"
    if theme not in VALID_THEMES:
        theme = "light"
    if tap_advance not in VALID_TAP_ADVANCE:
        tap_advance = "off"
    if default_sort not in VALID_SORTS:
        default_sort = "newest"
    return {
        "text_size": size,
        "text_weight": weight,
        "theme": theme,
        "tap_advance_enabled": tap_advance == "on",
        "default_sort": default_sort,
    }


@settings_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        size = request.form.get("text_size", "medium")
        weight = request.form.get("text_weight", "normal")
        theme = request.form.get("theme", "light")
        tap_advance = request.form.get("tap_advance", "off")
        default_sort = request.form.get("default_sort", "newest")
        if size not in VALID_TEXT_SIZES:
            size = "medium"
        if weight not in VALID_TEXT_WEIGHTS:
            weight = "normal"
        if theme not in VALID_THEMES:
            theme = "light"
        if tap_advance not in VALID_TAP_ADVANCE:
            tap_advance = "off"
        if default_sort not in VALID_SORTS:
            default_sort = "newest"
        resp = make_response(redirect(request.referrer or url_for("reader_bp.article_list")))
        resp.set_cookie(TEXT_SIZE_COOKIE, size, max_age=31536000)
        resp.set_cookie(TEXT_WEIGHT_COOKIE, weight, max_age=31536000)
        resp.set_cookie(THEME_COOKIE, theme, max_age=31536000)
        resp.set_cookie(TAP_ADVANCE_COOKIE, tap_advance, max_age=31536000)
        resp.set_cookie(SORT_COOKIE, default_sort, max_age=31536000)
        return resp
    return render_template("settings.html")
