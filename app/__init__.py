import os
import threading
import time
import uuid

from dotenv import load_dotenv
from typing import Any

from flask import Flask

load_dotenv()


def _prewarm_cache() -> None:
    time.sleep(2)  # Let gunicorn finish worker initialization
    try:
        from app.reader.api import fetch_article_list

        fetch_article_list(location="later")
        fetch_article_list(location="new")
    except Exception:
        pass  # Best-effort; real errors will surface on first user request


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "templates"))
    app = Flask(__name__, template_folder=template_dir)
    app.secret_key = os.environ.get("SECRET_KEY", uuid.uuid4().hex)
    if test_config:
        app.config.update(test_config)

    from app.dashboard import dashboard_bp
    from app.reader import reader_bp
    from app.settings import settings_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(reader_bp)
    app.register_blueprint(settings_bp)

    if not app.config.get("TESTING"):
        threading.Thread(target=_prewarm_cache, daemon=True).start()

    return app
