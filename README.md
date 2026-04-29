# Kindle Scribe Readwise Reader

A lightweight, server-side rendered web app for reading your Readwise Reader articles on a Kindle Scribe. No JavaScript, no images, no bloat — just text.

## Setup

1. **Configure your Readwise token:**

Get your access token from [readwise.io/access_token](https://readwise.io/access_token), then create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and replace `your_readwise_access_token_here` with your actual token. Optionally set `SECRET_KEY` to any random string (used for flash message session cookies).

2. **Start with Docker:**

```bash
docker compose up -d
```

The site runs at `http://127.0.0.1:5555`. Access it from your Kindle Scribe at `http://<your-machine-ip>:5555`.

The container automatically restarts on crash. To survive reboots, enable **"Start Docker Desktop when you log in"** in Docker Desktop → Settings → General.

## Docker commands

| Action | Command |
|--------|---------|
| Start | `docker compose up -d` |
| Stop | `docker compose down` |
| Logs | `docker compose logs -f` |
| Rebuild after code change | `docker compose up -d --build` |

## Usage

- **Article list** defaults to **All** and combines eligible items from Later and New only.
- Eligible items are **Articles** and **RSS** entries; archive, feed-only, and video items are excluded.
- Use location tabs (All / Later / New) to narrow the list when needed.
- **Filter by tag** using the tag picker at the top of the list — useful for keeping a focused reading queue.
- **Tap an article title** to read it. Content is stripped of images and media for fast loading on e-ink.
- **Archive** an article from the reader view with the **Archive** button. Archived items are intentionally excluded from list and reader access.
- **Refresh** the list manually if you've added new articles from another device.

## API Usage

The app caches all Readwise responses to disk so the cache survives container restarts and reboots. A cold cache makes at most **2 API calls** to load the All list view (one per location). Individual article fetches are also cached. Cached responses are reused for 20 minutes (list) or 60 minutes (articles).

On startup, each worker pre-warms the cache in the background. A distributed lock (backed by the same disk cache) ensures that concurrent workers never duplicate API calls for the same resource — at most one request fires per cache key even under load.

The Refresh button has a 2-minute cooldown. Hitting it within that window shows a brief notice and serves the existing cached list.

If a 429 is returned despite all this, the app waits and retries once before surfacing an error.

| Setting | Default | Override via |
|---------|---------|-------------|
| Cache directory | `<app_dir>/.cache` | `CACHE_DIR` env var |
| List cache TTL | 20 min | `LIST_CACHE_TTL` env var (seconds) |
| Article cache TTL | 60 min | `ARTICLE_CACHE_TTL` env var (seconds) |

## Reader Settings

The **Settings** panel — accessible from the reader view — lets you tune the reading experience for your display and preference:

- **Text size** — scale up or down from the default for comfortable reading on e-ink.
- **Font weight** — adjust between light and bold to suit your screen's contrast.
- **Dark mode** — invert to a dark background for low-light reading.
- **Sort order** — sort your article list by date added, or by note activity if you're working through annotated reading.

Settings persist across sessions.

## Kindle Scribe Browser Notes

This app is designed for the Kindle Scribe's experimental web browser:

- All server-side rendered HTML, zero client-side JavaScript
- Large touch targets for the touchscreen
- High contrast, no color, no animations
- Georgia/serif font stack for comfortable reading
- Minimal page weight to keep load times fast on e-ink
