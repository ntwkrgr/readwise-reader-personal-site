# Readwise Reader Personal Dashboard

## Running

The site runs as a Docker container. Start it with:

```bash
docker compose up -d
```

Access at: http://127.0.0.1:5555

The container uses `restart: unless-stopped` — it recovers from crashes automatically and starts on boot (requires Docker Desktop set to start at login).

## Setup

Requires a `.env` file with `READWISE_TOKEN=your_token_here` and `SECRET_KEY=any_random_string`. See README.md for the full environment variable reference and setup instructions.

## Architecture

Flask Blueprints package under `app/`. Entry point is `app.py`, a shim that calls the `create_app()` factory in `app/__init__.py`. In production, gunicorn serves `app:create_app()` with 2 workers.

| Route | Module |
|-------|--------|
| `/` | `app/dashboard.py` — home page |
| `/reader/` | `app/reader/` — Readwise Reader |
| `/highlights/`, `/highlights/all` | `app/highlights/` — Daily Review, paginated list |
| `/settings` | `app/settings.py` |
| (shared) | `app/cache.py`, `app/shared.py` — disk cache, Readwise API client |

Tests use pytest via `uv run pytest`; see Testing below for one-time setup.

## Testing

```bash
uv venv
uv pip install -r requirements.txt -r requirements-dev.txt
uv run playwright install chromium  # one-time; needed by tests/test_pagination_browser.py
uv run pytest
```

`tests/test_pagination_browser.py` renders the reading view in headless Chromium and asserts
no line ever straddles a computed page boundary. It skips cleanly if Chromium isn't installed.

## Gotchas

- `templates/` lives at the **repo root**, not under `app/` — `create_app()` overrides `template_folder` to point there (`app/__init__.py`).
- `create_app()` spawns a background cache-prewarm thread unless `TESTING` is set — tests must call `create_app({"TESTING": True})`.
- The Docker cache is a named volume (`cache:/app/.cache`); `docker compose up -d --build` does **not** clear it. Use `docker compose down -v` to wipe it.
- Gunicorn runs 2 workers; `app/cache.py` uses a `diskcache.Lock` (expire=30) so concurrent workers don't duplicate API calls.
- `ReadwiseAPIError` (`app/shared.py`) is the single error type every blueprint raises and every route catches into `templates/error.html`.
- Client-side JS must stay ES2015 / Chrome 75-compatible — the target browser is the Kindle Scribe's built-in browser.
- Tap-to-advance pagination (`templates/reader/_paginate.html`) measures real block-element positions from the rendered DOM to compute page boundaries — it's coupled to the reading-view CSS in `templates/base.html` (font, line-height, `article` element rules). Changing that CSS can shift where pages break; re-run `tests/test_pagination_browser.py` and re-check pagination on-device after reading-view CSS changes.
- Scrolling to a computed page start does **not** stop the browser from painting a full viewport's worth of content from that point — a naive "jump to the first overflowing line's top" approach still lets that line bleed onto the previous page, because the previous page's viewport paints past the intended boundary regardless. `_paginate.html` avoids this by moving whole block-level elements (`ATOM_TAGS`: p, li, headings, blockquote, pre, table, hr) past the boundary via an inserted blank spacer when they'd straddle it, rather than splitting mid-element.
- No linter, formatter, or CI is configured for this project.

## Common commands

| Action | Command |
|--------|---------|
| Start (Docker) | `docker compose up -d` |
| Stop | `docker compose down` |
| Wipe cache | `docker compose down -v` |
| Logs | `docker compose logs -f` |
| Rebuild | `docker compose up -d --build` |
| Local dev server | `python app.py` (Flask dev server, `debug=True`, port from `PORT` env, default 5555) |
| Test | `uv run pytest` |
