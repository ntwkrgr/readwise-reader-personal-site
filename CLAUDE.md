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
uv run pytest
```

## Gotchas

- `templates/` lives at the **repo root**, not under `app/` — `create_app()` overrides `template_folder` to point there (`app/__init__.py`).
- `create_app()` spawns a background cache-prewarm thread unless `TESTING` is set — tests must call `create_app({"TESTING": True})`.
- The Docker cache is a named volume (`cache:/app/.cache`); `docker compose up -d --build` does **not** clear it. Use `docker compose down -v` to wipe it.
- Gunicorn runs 2 workers; `app/cache.py` uses a `diskcache.Lock` (expire=30) so concurrent workers don't duplicate API calls.
- `ReadwiseAPIError` (`app/shared.py`) is the single error type every blueprint raises and every route catches into `templates/error.html`.
- Client-side JS must stay ES2015 / Chrome 75-compatible — the target browser is the Kindle Colorsoft's built-in experimental browser. This constraint carries over unverified from the Scribe (same Kindle firmware browser family); re-confirm via `navigator.userAgent` on-device before relying on any newer JS feature.
- The Colorsoft screen is ~7" (1264×1680, 300 ppi mono / 150 ppi color). `templates/` has no `@media` queries, so the layout is fully fluid — everything scales except `body { max-width: 800px }`. The real CSS viewport width (`window.innerWidth`) hasn't been measured on-device yet.
- Tap-to-advance pagination (`templates/reader/_paginate.html`) measures real line-box positions from the rendered DOM to compute page boundaries — it's coupled to the reading-view CSS in `templates/base.html` (font, line-height, `article` element rules). Changing that CSS can shift where pages break; re-check pagination on-device after reading-view CSS changes.
- The reading view (`templates/reader/read.html`) has a single `#reader-bar` fixed to the bottom of the screen (not an in-flow `.toolbar` like other pages). `.reader-bar` uses `flex-wrap: wrap`, so on a narrow viewport (or with Save Highlight showing) it can grow to two rows. Pagination measures its live height via `getBoundingClientRect()` each time it recomputes, subtracts that from the usable page height, and writes it back into `body`'s `padding-bottom` — so a taller/wrapped bar is accounted for automatically. Don't reintroduce a `.toolbar` measurement in `collectBoxes()`; the bar's own height computation replaces it.
- `#page-indicator` ("3 / 16") lives *inside* `#reader-bar` as an ordinary flex item (not absolutely positioned — that overlapped the Archive button on narrow viewports), so it never overlaps article text and can't overlap the buttons either. It's shown/hidden via `#article-content.highlight-mode-active ~ .reader-bar #page-indicator` in `templates/base.html` — keep that selector's DOM-nesting assumption (indicator inside `.reader-bar`) in mind if the bar markup is restructured.
- `collectBoxes()` in `templates/reader/_paginate.html` keeps `<pre>`/`<table>` atomic (one page-break-free box) only while the block fits within one page (`pageH`, computed per-recompute from viewport/text-size/bar-height). Past that it descends: per-line for `<pre>`, per-`<tr>` for `<table>`. This is device- and text-size-dependent — a block that fit whole on a larger screen or smaller text size may now split.
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
