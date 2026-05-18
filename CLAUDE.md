# Readwise Reader Personal Dashboard

## Running

The site runs as a Docker container. Start it with:

```bash
docker compose up -d
```

Access at: http://127.0.0.1:5555

The container uses `restart: unless-stopped` — it recovers from crashes automatically and starts on boot (requires Docker Desktop set to start at login).

## Setup

Requires `.env` file with `READWISE_TOKEN=your_token_here`.

Set `BIBLE_API_KEY` to enable the Bible navigator. The Bible feature uses API.Bible for NIV, NLT, and MSG; WEB/local bundled text is not exposed in the UI.

See README.md for full setup instructions.

## Architecture

Flask Blueprints package under `app/`. Each feature is a blueprint: `app/dashboard.py` is the home page at `/`, `app/reader/` is the Readwise Reader at `/reader/`, `app/highlights/` serves Daily Review at `/highlights/` and the paginated list at `/highlights/all`, `app/bible/` is the API.Bible navigator at `/bible/`, `app/settings.py` is Settings at `/settings`, and `app/cache.py` plus `app/shared.py` are shared utilities. Entry point is `app.py` shim pointing to `app/__init__.py` factory `create_app()`. Tests use pytest via `uv run pytest`.

## Common commands

| Action | Command |
|--------|---------|
| Start | `docker compose up -d` |
| Stop | `docker compose down` |
| Logs | `docker compose logs -f` |
| Rebuild | `docker compose up -d --build` |
