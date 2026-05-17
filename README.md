# Readwise Reader Personal Dashboard

A multi-feature personal dashboard built with Flask. It keeps the original Kindle-friendly Readwise Reader while adding a dashboard home, highlights review, and Bible navigation features.

## Features

- **Dashboard home** at `/` for navigating the available tools.
- **Readwise Reader** at `/reader/` for browsing and reading Readwise Reader articles.
- **Highlights Browser** at `/highlights/` with paginated Readwise highlights and daily review.
- **Bible Navigator** at `/bible/` with the WEB translation bundled locally and API.Bible optional for NIV/NLT/MSG.

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

## Environment Variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `READWISE_TOKEN` | Yes | none | Readwise access token used by the Reader and Highlights features. |
| `SECRET_KEY` | Yes | none | Flask session signing key for flash messages and preferences. |
| `PORT` | No | `5555` | HTTP port exposed by the Flask app and Docker container. |
| `CACHE_DIR` | No | `<app_dir>/.cache` | Disk cache location for API responses. |
| `LIST_CACHE_TTL` | No | `1200` | Readwise list cache TTL in seconds. |
| `ARTICLE_CACHE_TTL` | No | `3600` | Readwise article cache TTL in seconds. |
| `BIBLE_API_KEY` | No | none | Enables NIV/NLT/MSG through API.Bible. |
| `BIBLE_CACHE_TTL` | No | `1209600` | Bible API cache TTL in seconds, capped at the API.Bible ToS max of 14 days. |

## Usage

### Dashboard Home

Open `/` for a simple launch point into the dashboard features. Use it when switching between reading articles, reviewing highlights, and navigating Bible passages.

### Readwise Reader

- Open `/reader/` to browse your Readwise Reader queue.
- The article list defaults to **All** and combines eligible items from Later and New only.
- Eligible items are **Articles** and **RSS** entries; archive, feed-only, and video items are excluded.
- Use location tabs (All / Later / New) to narrow the list when needed.
- Filter by tag using the tag picker at the top of the list.
- Tap an article title to read it. Content is stripped of images and media for fast loading on e-ink.
- Archive an article from the reader view with the **Archive** button. Archived items are intentionally excluded from list and reader access.
- Refresh the list manually if you've added new articles from another device.

### Highlights Browser

- Open `/highlights/` to browse paginated Readwise highlights.
- Use the daily review flow to revisit saved highlights in smaller batches.
- Highlight saving uses minimal JavaScript for interaction feedback.

### Bible Navigator

- Open `/bible/` to navigate Bible books, chapters, and verses.
- WEB is available from bundled local data without an external API key.
- The bundled data/web.json is a development stub with partial WEB text. For the full WEB Bible, see openbible.info/codes/web and replace data/web.json.
- NIV, NLT, and MSG require an API.Bible key (free tier available). NLT and MSG translation IDs are placeholders -- verify against api.bible/bibles before use.
- Minimal JS is used for highlight saving and Bible navigation (ES2015/Chrome 75+ only).

## API Usage and Caching

The app caches Readwise responses to disk so the cache survives container restarts and reboots. A cold cache makes at most **2 API calls** to load the All reader list view (one per location). Individual article fetches are also cached. Cached Readwise responses are reused for 20 minutes (list) or 60 minutes (articles) by default.

On startup, each worker pre-warms the cache in the background. A distributed lock (backed by the same disk cache) ensures that concurrent workers never duplicate API calls for the same resource; at most one request fires per cache key even under load.

The Refresh button has a 2-minute cooldown. Hitting it within that window shows a brief notice and serves the existing cached list.

If a 429 is returned despite all this, the app waits and retries once before surfacing an error.

Bible API responses are cached separately according to `BIBLE_CACHE_TTL`, which defaults to 14 days.

## Reader Settings

The **Settings** panel lets you tune the reading experience for your display and preference:

- **Text size** -- scale up or down from the default for comfortable reading on e-ink.
- **Font weight** -- adjust between light and bold to suit your screen's contrast.
- **Dark mode** -- invert to a dark background for low-light reading.
- **Sort order** -- sort your article list by date added, or by note activity if you're working through annotated reading.

Settings persist across sessions.

## Kindle Scribe Browser Notes

The reader experience is designed for the Kindle Scribe's experimental web browser:

- Server-side rendered HTML with minimal client-side JavaScript where needed
- Large touch targets for the touchscreen
- High contrast, no color-dependent controls, no animations
- Georgia/serif font stack for comfortable reading
- Minimal page weight to keep load times fast on e-ink
