# Home Page Weather Hero and Section Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the home page's plain link list with a weather hero card and color-accented Reader / Highlights / Notebook cards (plus Settings) with inline SVG icons, legible on the Kindle Colorsoft in light and dark themes.

**Architecture:** A new `app/weather.py` fetches current conditions server-side from Open-Meteo through the existing `cached_fetch` disk cache and returns a small dict, or `None` on any failure. `app/dashboard.py` passes that dict to `templates/dashboard.html`, which renders the hero card (colored icons from a `weather_icon(name)` macro in `templates/_weather_icons.html`) above four stacked section cards. All styling is page-local CSS with color only on stripes, icon tiles, and weather icons; the page has no JavaScript.

**Tech Stack:** Flask / Jinja2, `requests`, `diskcache` (via `app/cache.py`), Open-Meteo forecast API, inline SVG, pytest via `uv run pytest`.

**Spec:** https://github.com/ntwkrgr/readwise-reader-personal-site/issues/24

## Global Constraints

- **Browser:** Kindle Colorsoft experimental browser (Chrome 75 family). The home page adds no JavaScript; any future JS must be ES2015. CSS must work in Chrome 75: no flexbox `gap` (Chrome 84+; space flex items with margins), no `@media` queries (layout stays fluid inside `body { max-width: 800px }`), no `aspect-ratio`.
- **Existing template guards** (`tests/test_routes.py`): nothing under `templates/` may contain `linear-gradient`, `sans-serif`, `Arial`, `-apple-system`, `BlinkMacSystemFont`, or `Segoe UI`.
- **Text stays black/white:** black on white in the light theme, white on black in the dark theme. Color appears only on card left stripes, icon tiles, and weather icons.
- **Themes:** dark rules use `body.theme-dark …` (the auto theme sets that class from JS in `templates/base.html`). In `templates/dashboard.html` they recolor borders per side (`border-top-color`, `border-right-color`, `border-bottom-color`) — never the `border-color` shorthand, which would also turn the colored left stripe white.
- **Palette (exact):** Reader `#1565c0`, Highlights `#ef6c00`, Notebook `#2e7d32`, Settings `#546e7a`. Weather: amber `#ffa000` (sun, lightning; stripe for clear / partly / storm), indigo `#5c6bc0` (moon; night stripe), gray `#90a4ae` (clouds, fog; stripe for cloudy / fog / unavailable), blue `#1e88e5` (rain), light blue `#039be5` (snow).
- **Icons:** inline SVG only — no icon fonts, CDNs, or image files. Section icons are 24×24 line icons (`stroke="currentColor"`, white on the colored tile), the same style as the reader bar in `templates/reader/read.html`. Weather icons are 64×64 filled color SVGs from the `weather_icon(name)` macro.
- **Weather data:** Open-Meteo `https://api.open-meteo.com/v1/forecast`, no API key, fetched server-side through `app.cache.cached_fetch` (TTL 1800 s), request timeout 5 s, Fahrenheit. Location from env `WEATHER_LAT` (default `31.4638`), `WEATHER_LON` (default `-100.4370`), `WEATHER_LOCATION` (default `San Angelo`). `fetch_weather()` returns `None` on any failure; `GET /` returns 200 whether or not weather is available.
- **Weather dict contract** (`fetch_weather()` → template): `{"temp": int, "high": int, "low": int, "condition": str, "icon": str, "location": str}`; `icon` is one of `clear`, `night`, `partly`, `cloudy`, `fog`, `rain`, `snow`, `storm`.
- **Settings stays reachable:** last card on the home page, pinned to the bottom of the screen with `margin-top: auto`.
- **Tests stay offline:** no test may call Open-Meteo. `tests/test_weather.py` mocks `requests.get`; `tests/conftest.py` (Task 3) stubs `app.dashboard.fetch_weather` for every test.
- **Code comments:** comment each function and each CSS / template block pragmatically — what it does, not why it exists.
- **Visual checks:** each visual task captures and reads its own screenshots (Browser pane, 632×840 viewport, light and dark). Anything a screenshot check notices goes to the reviewer even if no acceptance criterion covers it. Local servers must not use port 5555 — the Docker container owns it.
- **Commits:** one commit per task, staging explicit paths only (never `.codex-screenshots/` or `.claude/launch.json`); end the message with the attribution trailer your session provides.

**User decisions (already made):**
- "Redesign home page to include weather hero card, and show Reader/Highlights/Notebook in cards below with coresponding icons."
- "plan it, but also include color elements since I'll use it on a colorsoft."

## Review Focus

1. **Open-Meteo slow or unreachable** → the home page still loads within a few seconds and shows "Weather unavailable". Pinned by Task 1 (`test_fetch_weather_requests_configured_location_in_fahrenheit` asserts a timeout ≤ 5 s; `test_network_error_returns_none`) and Task 3 (`test_weather_unavailable_still_renders_home`).
2. **Open-Meteo answers 200 with a partial or odd payload** (no `daily` block, `null` temperature, `{}`) → fallback card, never a 500. Pinned by Task 1 `test_malformed_payload_returns_none`.
3. **A one-off failure sticking around** → failures must not be cached; the next home page load retries. Pinned by Task 1 `test_failed_fetch_is_not_cached`.
4. **An icon name with no drawing** (including `night` and the unknown-code fallback) → the hero must never show an empty icon box. Pinned by Task 1 (unknown code maps to `cloudy`) and Task 3 `test_every_weather_icon_has_an_svg`.
5. **Dark (or auto-dark) theme dropping the color accents** → stripes keep their colors on black. Pinned by Task 2 `test_dark_theme_keeps_colored_stripes`.

## Deferred decisions

The issue leaves these open. Each was decided as below so work can proceed; a human should review them before merge. None changes the task structure.

1. **Weather source: Open-Meteo.** The issue names none. Free, no key, and one request returns current conditions plus today's high/low. Alternative: NWS `api.weather.gov` (US-only, needs a User-Agent and a two-step grid lookup). Unchanged either way: server-side fetch, disk cache, fallback card.
2. **Location via env, defaulting to San Angelo, TX** (`WEATHER_LAT=31.4638`, `WEATHER_LON=-100.4370`, `WEATHER_LOCATION=San Angelo`), mirroring how `NOTES_TZ` defaults to `America/Chicago`. Not on the Settings page: Settings are per-browser cookies, while the weather location is server-wide. Changing it is three lines in `.env`.
3. **Fahrenheit, hard-coded.** No units setting.
4. **Hero content:** current temperature, condition, today's high/low, place name. No multi-day forecast, date, wind, humidity, or "updated at".
5. **Failures aren't cached.** While Open-Meteo is unreachable, each home page load waits up to 5 s, then shows "Weather unavailable". Alternative: cache failures for a few minutes (more code).
6. **"Home" heading removed** (Task 3) so the hero card is the first thing on the page; the browser tab title stays "Home".
7. **Stacked full-width cards, not a 3-up grid.** The Colorsoft's CSS viewport width hasn't been measured; full-width rows stay legible and easy to tap at any width.
8. **Color treatment:** a 10 px colored left stripe plus a solid colored icon tile with a white icon per card; the weather card's stripe follows the condition. No background tints — pastels wash out on Kaleido 3 and lower text contrast.
9. **Night:** only a clear sky swaps to a moon; partly cloudy at night still shows the sun behind a cloud.
10. **Settings is a fourth card** (gray, sliders icon), pinned to the bottom as it is today.
11. **Static card subtitles:** "Shortlist and Later", "Daily Review", "Journal and to-dos", "Theme, text, and sorting".
12. **README's "deliberately monochrome" note is narrowed:** reading views stay monochrome; the home page uses color accents.
13. **Screenshot viewport 632×840** assumes 1264×1680 at device-pixel-ratio 2; re-check on the device.
14. **Existing dashboard tests** in `tests/test_routes.py` and `tests/test_notebook.py` assert the old `dashboard-link` classes; they move into one new `tests/test_dashboard.py`.

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `app/weather.py` (new) | Fetch and normalize Open-Meteo current conditions, cached; `None` on failure | 1 |
| `tests/test_weather.py` (new) | Weather client tests with mocked HTTP | 1 |
| `templates/dashboard.html` | Home page: hero card + section cards, page-local CSS | 2, 3 |
| `tests/test_dashboard.py` (new) | Home page rendering tests | 2, 3 |
| `templates/_weather_icons.html` (new) | `weather_icon(name)` macro: one colored SVG per icon name | 3 |
| `app/dashboard.py` | Pass `fetch_weather()` to the template | 3 |
| `tests/conftest.py` (new) | Autouse stub keeping every test offline | 3 |
| `README.md`, `.env.example`, `CLAUDE.md` | Env vars, usage, caching, Colorsoft notes | 1, 2, 3 |

Tasks 1 and 2 are independent; Task 3 needs both.

---

### Task 1: Open-Meteo weather client

**Goal:** Add `app/weather.py`, whose `fetch_weather()` returns today's normalized weather from Open-Meteo (cached 30 minutes) or `None` on any failure, with the new env vars documented.

**Files:**
- Create: `app/weather.py`
- Create: `tests/test_weather.py`
- Modify: `README.md:56` (Environment Variables table — add three rows after `NOTES_TZ`)
- Modify: `.env.example` (append a weather block at the end)

**Acceptance Criteria:**
- [ ] For a mocked Open-Meteo reply, `fetch_weather()` returns `{"temp", "high", "low", "condition", "icon", "location"}` with temperatures rounded to ints
- [ ] The request goes to Open-Meteo with `WEATHER_LAT` / `WEATHER_LON`, `temperature_unit=fahrenheit`, and a timeout of at most 5 s
- [ ] WMO codes map to their condition label and icon; a clear sky at night maps to `night`; an unknown code maps to `("Unknown", "cloudy")`
- [ ] A network error, an HTTP error, or a malformed payload makes `fetch_weather()` return `None` without raising
- [ ] A successful result is cached (two lookups, one HTTP call); a failure is not cached (the next call retries)
- [ ] A live call against Open-Meteo returns a dict, not `None`
- [ ] README's env table and `.env.example` document `WEATHER_LAT`, `WEATHER_LON`, `WEATHER_LOCATION`
- [ ] `uv run pytest` passes

**Verify:** `uv run pytest tests/test_weather.py -v && uv run pytest` → 17 passed in `tests/test_weather.py`, then the whole suite passes

**Steps:**

- [ ] **Step 1: Set up the test environment (skip if `.venv/` already exists)**

```bash
[ -d .venv ] || (uv venv && uv pip install -r requirements.txt -r requirements-dev.txt)
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_weather.py`:

```python
"""Tests for the Open-Meteo weather client used by the home page."""
from unittest.mock import MagicMock, patch

import diskcache
import pytest
import requests

from app import cache as cache_module
from app import weather


def _payload(code=2, is_day=1, temp=71.6):
    """Build an Open-Meteo-shaped reply with the given weather code, day flag, and current temperature."""
    return {
        "current": {"temperature_2m": temp, "weather_code": code, "is_day": is_day},
        "daily": {"temperature_2m_max": [78.4], "temperature_2m_min": [54.9]},
    }


def _response(payload=None, status_error=None):
    """Build a fake requests.Response whose json() returns payload; raise_for_status() raises status_error if given."""
    resp = MagicMock()
    resp.json.return_value = payload
    if status_error:
        resp.raise_for_status.side_effect = status_error
    return resp


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path):
    """Give each test an empty disk cache so cached weather never leaks between tests."""
    cache = diskcache.Cache(str(tmp_path / "cache"))
    with patch.object(cache_module, "_cache", cache):
        yield cache
    cache.close()


def test_fetch_weather_normalizes_open_meteo_reply():
    with patch.object(weather.http_requests, "get", return_value=_response(_payload())):
        result = weather.fetch_weather()
    assert result == {
        "temp": 72,
        "high": 78,
        "low": 55,
        "condition": "Partly cloudy",
        "icon": "partly",
        "location": weather.WEATHER_LOCATION,
    }


def test_fetch_weather_requests_configured_location_in_fahrenheit():
    with patch.object(weather.http_requests, "get", return_value=_response(_payload())) as mock_get:
        weather.fetch_weather()
    params = mock_get.call_args.kwargs["params"]
    assert mock_get.call_args.args[0] == weather.OPEN_METEO_URL
    assert params["latitude"] == weather.WEATHER_LAT
    assert params["longitude"] == weather.WEATHER_LON
    assert params["temperature_unit"] == "fahrenheit"
    assert mock_get.call_args.kwargs["timeout"] <= 5


@pytest.mark.parametrize("code, is_day, condition, icon", [
    (0, 1, "Clear", "clear"),
    (0, 0, "Clear", "night"),
    (2, 0, "Partly cloudy", "partly"),
    (45, 1, "Fog", "fog"),
    (63, 1, "Rain", "rain"),
    (75, 1, "Heavy snow", "snow"),
    (95, 1, "Thunderstorm", "storm"),
    (42, 1, "Unknown", "cloudy"),
])
def test_weather_code_maps_to_condition_and_icon(code, is_day, condition, icon):
    with patch.object(weather.http_requests, "get", return_value=_response(_payload(code, is_day))):
        result = weather.fetch_weather()
    assert (result["condition"], result["icon"]) == (condition, icon)


def test_network_error_returns_none():
    with patch.object(weather.http_requests, "get", side_effect=requests.ConnectionError("down")):
        assert weather.fetch_weather() is None


def test_http_error_returns_none():
    resp = _response(status_error=requests.HTTPError("400 Bad Request"))
    with patch.object(weather.http_requests, "get", return_value=resp):
        assert weather.fetch_weather() is None


@pytest.mark.parametrize("payload", [
    {"current": {"temperature_2m": 70, "weather_code": 0, "is_day": 1}},  # no daily block
    _payload(temp=None),  # null current temperature
    {},  # empty JSON object
])
def test_malformed_payload_returns_none(payload):
    with patch.object(weather.http_requests, "get", return_value=_response(payload)):
        assert weather.fetch_weather() is None


def test_weather_is_cached_between_calls():
    with patch.object(weather.http_requests, "get", return_value=_response(_payload())) as mock_get:
        first = weather.fetch_weather()
        second = weather.fetch_weather()
    assert first == second
    assert mock_get.call_count == 1


def test_failed_fetch_is_not_cached():
    replies = [requests.ConnectionError("down"), _response(_payload())]
    with patch.object(weather.http_requests, "get", side_effect=replies) as mock_get:
        assert weather.fetch_weather() is None
        assert weather.fetch_weather()["temp"] == 72
    assert mock_get.call_count == 2
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_weather.py -v`
Expected: collection error — `ImportError: cannot import name 'weather' from 'app'`

- [ ] **Step 4: Write the implementation**

Create `app/weather.py`:

```python
"""Current weather for the home page hero card, from Open-Meteo (free, no API key)."""

import os
from typing import Any

import requests as http_requests

from app.cache import cached_fetch

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
# Location for the weather card; defaults to San Angelo, TX (override in .env)
WEATHER_LAT = os.environ.get("WEATHER_LAT", "31.4638")
WEATHER_LON = os.environ.get("WEATHER_LON", "-100.4370")
WEATHER_LOCATION = os.environ.get("WEATHER_LOCATION", "San Angelo")
WEATHER_CACHE_TTL = 1800  # 30 minutes
WEATHER_TIMEOUT = 5  # seconds to wait for Open-Meteo before giving up

# WMO weather code -> (condition label, icon name drawn by templates/_weather_icons.html)
WMO_CODES: dict[int, tuple[str, str]] = {
    0: ("Clear", "clear"),
    1: ("Mostly clear", "partly"),
    2: ("Partly cloudy", "partly"),
    3: ("Overcast", "cloudy"),
    45: ("Fog", "fog"),
    48: ("Fog", "fog"),
    51: ("Drizzle", "rain"),
    53: ("Drizzle", "rain"),
    55: ("Drizzle", "rain"),
    56: ("Freezing drizzle", "rain"),
    57: ("Freezing drizzle", "rain"),
    61: ("Light rain", "rain"),
    63: ("Rain", "rain"),
    65: ("Heavy rain", "rain"),
    66: ("Freezing rain", "rain"),
    67: ("Freezing rain", "rain"),
    71: ("Light snow", "snow"),
    73: ("Snow", "snow"),
    75: ("Heavy snow", "snow"),
    77: ("Snow grains", "snow"),
    80: ("Showers", "rain"),
    81: ("Showers", "rain"),
    82: ("Heavy showers", "rain"),
    85: ("Snow showers", "snow"),
    86: ("Snow showers", "snow"),
    95: ("Thunderstorm", "storm"),
    96: ("Thunderstorm", "storm"),
    99: ("Thunderstorm", "storm"),
}


def _fetch_current() -> dict[str, Any]:
    """Call Open-Meteo and reduce the reply to the fields the hero card shows; raises on any failure."""
    resp = http_requests.get(
        OPEN_METEO_URL,
        params={
            "latitude": WEATHER_LAT,
            "longitude": WEATHER_LON,
            "current": "temperature_2m,weather_code,is_day",
            "daily": "temperature_2m_max,temperature_2m_min",
            "temperature_unit": "fahrenheit",
            "timezone": "auto",
            "forecast_days": 1,
        },
        timeout=WEATHER_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    current, daily = data["current"], data["daily"]
    condition, icon = WMO_CODES.get(current["weather_code"], ("Unknown", "cloudy"))
    # Clear sky at night gets a moon instead of a sun
    if icon == "clear" and not current["is_day"]:
        icon = "night"
    return {
        "temp": round(current["temperature_2m"]),
        "high": round(daily["temperature_2m_max"][0]),
        "low": round(daily["temperature_2m_min"][0]),
        "condition": condition,
        "icon": icon,
        "location": WEATHER_LOCATION,
    }


def fetch_weather() -> dict[str, Any] | None:
    """Return current weather (cached 30 min), or None when it can't be fetched so the home page still renders."""
    try:
        return cached_fetch(f"weather:{WEATHER_LAT}:{WEATHER_LON}", _fetch_current, WEATHER_CACHE_TTL)
    except Exception:  # Network, HTTP, or payload problems all just hide the weather
        return None
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_weather.py -v`
Expected: 17 passed

- [ ] **Step 6: Check the real API shape once**

Run: `uv run python -c "from app.weather import fetch_weather; print(fetch_weather())"`
Expected: a dict such as `{'temp': 64, 'high': 71, 'low': 48, 'condition': 'Overcast', 'icon': 'cloudy', 'location': 'San Angelo'}` (values vary). This writes to the gitignored local `.cache/`. If it prints `None`, compare against the raw reply: `curl -s 'https://api.open-meteo.com/v1/forecast?latitude=31.4638&longitude=-100.4370&current=temperature_2m,weather_code,is_day&daily=temperature_2m_max,temperature_2m_min&temperature_unit=fahrenheit&timezone=auto&forecast_days=1'` and fix the parsing (and the test payload) to match. If the machine is offline, say so in the task report instead of guessing.

- [ ] **Step 7: Document the env vars**

In `README.md`, add these rows to the Environment Variables table directly after the `NOTES_TZ` row:

```markdown
| `WEATHER_LAT` | No | `31.4638` | Latitude for the home page weather card (default: San Angelo, TX). |
| `WEATHER_LON` | No | `-100.4370` | Longitude for the home page weather card. |
| `WEATHER_LOCATION` | No | `San Angelo` | Place name shown on the weather card. |
```

Append to `.env.example`:

```bash
# Optional: home page weather location (Open-Meteo; no API key needed).
# Defaults to San Angelo, TX.
# WEATHER_LAT=31.4638
# WEATHER_LON=-100.4370
# WEATHER_LOCATION=San Angelo
```

- [ ] **Step 8: Run the full suite**

Run: `uv run pytest`
Expected: all tests pass

- [ ] **Step 9: Commit**

```bash
git add app/weather.py tests/test_weather.py README.md .env.example
git commit -m "feat: add cached Open-Meteo weather client for the home page"
```

---

### Task 2: Color-accented section cards on the home page

**Goal:** Replace the home page's plain link list with stacked Reader, Highlights, Notebook, and Settings cards, each with a colored left stripe and a colored icon tile holding a white inline SVG icon, legible in light and dark themes.

**Files:**
- Modify: `templates/dashboard.html` (full rewrite)
- Create: `tests/test_dashboard.py`
- Modify: `tests/test_routes.py:50-65` (delete `test_dashboard_renders_feature_links` and `test_dashboard_places_settings_link_at_bottom`)
- Modify: `tests/test_notebook.py:259-275` (delete the `# --- dashboard integration ---` section and its two tests)
- Modify: `README.md:7` (Features bullet) and `README.md:62` (Dashboard Home paragraph)

**Acceptance Criteria:**
- [ ] The home page renders Reader, Highlights, Notebook, and Settings as `dashboard-card` links in that order, each with its `card-<name>` accent class, a `dashboard-card-title` label, and an inline `<svg>` inside a `dashboard-card-icon` tile
- [ ] The old `dashboard-link` list is gone
- [ ] The Settings card carries `dashboard-settings-link` and the page CSS pins it with `margin-top: auto`
- [ ] `templates/dashboard.html` contains no `border-color:` shorthand, so dark theme keeps the colored stripes
- [ ] The dashboard tests that asserted the old classes are gone from `tests/test_routes.py` and `tests/test_notebook.py`
- [ ] Screenshots at 632×840 (light, dark) and 375×812 (light) were captured and read, and the Step 7 checklist holds
- [ ] README's Features bullet and Dashboard Home paragraph describe the cards
- [ ] `uv run pytest` passes

**Verify:** `uv run pytest tests/test_dashboard.py -v && uv run pytest` → 5 passed in `tests/test_dashboard.py`, then the whole suite passes

**Steps:**

- [ ] **Step 1: Set up the test environment (skip if `.venv/` already exists)**

```bash
[ -d .venv ] || (uv venv && uv pip install -r requirements.txt -r requirements-dev.txt)
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_dashboard.py`:

```python
"""Tests for the home page."""
from pathlib import Path

import pytest

from app import create_app

DASHBOARD_TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "dashboard.html"
# (accent class, card title, link) for each home page card, in page order
SECTION_CARDS = (
    ("card-reader", "Reader", "/reader/"),
    ("card-highlights", "Highlights", "/highlights/"),
    ("card-notebook", "Notebook", "/notebook/"),
    ("card-settings", "Settings", "/settings"),
)


@pytest.fixture
def client():
    flask_app = create_app({"TESTING": True})
    with flask_app.test_client() as c:
        yield c


def _home_html(client):
    """GET the home page, check it rendered, and return its HTML."""
    resp = client.get("/")
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def test_section_cards_link_to_each_tool_in_order(client):
    html = _home_html(client)
    positions = [html.index(f'href="{href}"') for _, _, href in SECTION_CARDS]
    assert positions == sorted(positions)


def test_each_section_card_has_accent_icon_and_label(client):
    html = _home_html(client)
    for card_class, label, _ in SECTION_CARDS:
        assert f'class="dashboard-card {card_class}' in html
        assert f'<span class="dashboard-card-title">{label}</span>' in html
    assert html.count('<span class="dashboard-card-icon"><svg') == len(SECTION_CARDS)


def test_settings_card_is_pinned_to_the_bottom(client):
    html = _home_html(client)
    assert 'class="dashboard-card card-settings dashboard-settings-link"' in html
    assert "margin-top: auto" in html


def test_old_plain_link_list_is_gone(client):
    assert "dashboard-link" not in _home_html(client)


def test_dark_theme_keeps_colored_stripes():
    """Dark rules must recolor borders side by side; a `border-color` shorthand would also turn the colored left stripe white."""
    assert "border-color:" not in DASHBOARD_TEMPLATE.read_text()
```

Then delete the two old home page tests that assert the `dashboard-link` classes:
- `tests/test_routes.py` lines 50-65: `test_dashboard_renders_feature_links` and `test_dashboard_places_settings_link_at_bottom` (keep the `# --- Article list ---` comment and everything else).
- `tests/test_notebook.py` lines 259-275: the `# --- dashboard integration ---` comment, `test_dashboard_includes_notebook_link`, and `test_dashboard_settings_link_still_last` (the file then ends with `test_note_detail_missing_file_shows_error`).

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_dashboard.py -v`
Expected: 4 failed, 1 passed. `test_section_cards_link_to_each_tool_in_order` already passes (the old list has the same order — it guards the order through the rewrite); the other four fail on the missing `dashboard-card` markup, the remaining `dashboard-link` classes, and the `border-color: #fff` in the old dark rule.

- [ ] **Step 4: Rewrite the home page template**

Replace the whole of `templates/dashboard.html` with:

```html
{% extends "base.html" %}

{% block title %}Home{% endblock %}

{% block styles %}
<style>
    /* Page heading */
    .dashboard-title {
        font-size: 28px;
        line-height: 1.2;
        font-weight: 700;
        margin: 0 0 20px 0;
        color: #000;
    }
    /* Home page column: fills the screen so the Settings card can sit at the bottom */
    .dashboard-menu {
        display: flex;
        flex-direction: column;
        min-height: calc(100vh - 84px);
        margin: 0;
    }
    /* Section card: colored left stripe, colored icon tile, black/white text */
    .dashboard-card {
        display: flex;
        align-items: center;
        min-height: 72px;
        padding: 10px 14px;
        margin: 0 0 12px 0;
        border: 2px solid #000;
        border-left: 10px solid #000;
        border-radius: 12px;
        background: #fff;
        color: #000;
        text-decoration: none;
    }
    /* Square colored tile holding the white line icon */
    .dashboard-card-icon {
        flex: 0 0 48px;
        width: 48px;
        height: 48px;
        margin-right: 14px;
        padding: 10px;
        border-radius: 10px;
        color: #fff;
    }
    .dashboard-card-icon svg {
        display: block;
        width: 100%;
        height: 100%;
    }
    /* Card title */
    .dashboard-card-title {
        display: block;
        font-size: 22px;
        line-height: 1.2;
        font-weight: 700;
    }
    /* One-line description under the title */
    .dashboard-card-sub {
        display: block;
        font-size: 15px;
        line-height: 1.3;
    }
    /* Per-section accent: stripe and icon tile share one color */
    .card-reader { border-left-color: #1565c0; }
    .card-reader .dashboard-card-icon { background: #1565c0; }
    .card-highlights { border-left-color: #ef6c00; }
    .card-highlights .dashboard-card-icon { background: #ef6c00; }
    .card-notebook { border-left-color: #2e7d32; }
    .card-notebook .dashboard-card-icon { background: #2e7d32; }
    .card-settings { border-left-color: #546e7a; }
    .card-settings .dashboard-card-icon { background: #546e7a; }
    /* Settings card: pushed to the bottom of the screen */
    .dashboard-settings-link {
        margin-top: auto;
        margin-bottom: 0;
    }
    /* Dark theme: flip text and background; recolor only the plain borders so colored stripes stay */
    body.theme-dark .dashboard-title {
        color: #fff;
    }
    body.theme-dark .dashboard-card {
        background: #000;
        color: #fff;
        border-top-color: #fff;
        border-right-color: #fff;
        border-bottom-color: #fff;
    }
</style>
{% endblock %}

{% block nav %}
<h1 class="dashboard-title">Home</h1>
{% endblock %}

{% block content %}
<main class="dashboard-menu">
    {# Section cards: one per tool, each with its own accent color and icon #}
    <a class="dashboard-card card-reader" href="{{ url_for('reader_bp.article_list') }}">
        <span class="dashboard-card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z"/><path d="M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z"/></svg></span>
        <span class="dashboard-card-text">
            <span class="dashboard-card-title">Reader</span>
            <span class="dashboard-card-sub">Shortlist and Later</span>
        </span>
    </a>
    <a class="dashboard-card card-highlights" href="{{ url_for('highlights_bp.daily_review') }}">
        <span class="dashboard-card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 013 3L7 19l-4 1 1-4z"/></svg></span>
        <span class="dashboard-card-text">
            <span class="dashboard-card-title">Highlights</span>
            <span class="dashboard-card-sub">Daily Review</span>
        </span>
    </a>
    <a class="dashboard-card card-notebook" href="{{ url_for('notebook_bp.index') }}">
        <span class="dashboard-card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M16 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V8z"/><path d="M15 3v5h6"/><path d="M7 13h10M7 17h6"/></svg></span>
        <span class="dashboard-card-text">
            <span class="dashboard-card-title">Notebook</span>
            <span class="dashboard-card-sub">Journal and to-dos</span>
        </span>
    </a>
    {# Settings stays reachable, pinned to the bottom of the screen #}
    <a class="dashboard-card card-settings dashboard-settings-link" href="{{ url_for('settings_bp.settings') }}">
        <span class="dashboard-card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/></svg></span>
        <span class="dashboard-card-text">
            <span class="dashboard-card-title">Settings</span>
            <span class="dashboard-card-sub">Theme, text, and sorting</span>
        </span>
    </a>
</main>
{% endblock %}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_dashboard.py -v`
Expected: 5 passed

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest`
Expected: all tests pass (`test_templates_do_not_force_sans_serif_fonts` and `test_templates_do_not_render_tap_fade_overlays` included)

- [ ] **Step 7: Screenshot the cards and read the screenshots**

The home page has no JS or external assets, so its server-rendered HTML saved to a static file looks exactly like the live page. `.codex-screenshots/` is gitignored, so nothing written there gets committed.

Render the page in both themes:

```bash
mkdir -p .codex-screenshots
cat > .codex-screenshots/render_home.py <<'EOF'
"""Save the server-rendered home page as static HTML for screenshot checks (scratch; never committed)."""
from pathlib import Path

from app import create_app

OUT = Path(".codex-screenshots")
client = create_app({"TESTING": True}).test_client()

# One file per theme: home-light.html, home-dark.html
for theme in ("light", "dark"):
    client.set_cookie("readwise_theme", theme)
    (OUT / f"home-{theme}.html").write_text(client.get("/").get_data(as_text=True), encoding="utf-8")
EOF
PYTHONPATH=. uv run python .codex-screenshots/render_home.py && ls .codex-screenshots
```

Expected: `home-dark.html  home-light.html  render_home.py`

Serve the folder on port 5557 (5555 belongs to the Docker container). Create `.claude/launch.json` if it doesn't exist (local tooling — don't commit it; if it exists without a `home-shots` entry, add the entry by hand):

```bash
mkdir -p .claude && [ -f .claude/launch.json ] || cat > .claude/launch.json <<EOF
{"version": "0.0.1", "configurations": [{"name": "home-shots", "runtimeExecutable": "python3", "runtimeArgs": ["-m", "http.server", "5557", "--bind", "127.0.0.1", "--directory", "$PWD/.codex-screenshots"], "port": 5557}]}
EOF
```

Then, with the Browser pane tools (`mcp__Claude_Browser__*`):
1. `preview_start` with name `home-shots`. If it can't find that config, run `python3 -m http.server 5557 --bind 127.0.0.1 --directory "$PWD/.codex-screenshots"` with Bash `run_in_background` and call `preview_start` with url `http://127.0.0.1:5557/home-light.html`.
2. `resize_window` width 632, height 840 → `navigate` to `http://127.0.0.1:5557/home-light.html` → `computer` action `screenshot`.
3. `navigate` to `http://127.0.0.1:5557/home-dark.html` → `screenshot`.
4. `resize_window` width 375, height 812 → `navigate` to `http://127.0.0.1:5557/home-light.html` → `screenshot`.
5. `resize_window` preset `desktop`, then `preview_stop` (or stop the background server).

Read each screenshot and confirm:
- Light (632 wide): "Home" heading, then Reader (blue), Highlights (orange), and Notebook (green) cards stacked full width, then the Settings card (gray) at the bottom of the screen. Each card has a colored left stripe and a colored square tile with a white icon (open book, highlighter pen, note page, sliders). Titles are bold black, subtitles sit under them, and nothing is underlined.
- Dark: same layout with white text and white top/right/bottom borders on black; stripes and tiles keep their colors.
- 375 wide: cards fit with no horizontal scrolling; text wraps instead of overflowing.

If anything is off, fix the CSS or SVG, re-run the render script, re-take the screenshots, and re-run `uv run pytest`. If the Browser pane tools aren't available to you, don't skip this step: report it as blocked so the coordinator runs it.

- [ ] **Step 8: Update the README**

In `README.md`, replace the Features bullet

```markdown
- **Dashboard home** at `/` for navigating the available tools.
```

with

```markdown
- **Dashboard home** at `/` with a color-coded card and icon for each tool.
```

and replace the paragraph under `### Dashboard Home` (the one starting "Open `/` for a simple launch point") with:

```markdown
Open `/` for the launch point into the dashboard features. Reader, Highlights, and Notebook each get a card with its own accent color and icon; Settings sits at the bottom of the screen.
```

- [ ] **Step 9: Commit**

```bash
git add templates/dashboard.html tests/test_dashboard.py tests/test_routes.py tests/test_notebook.py README.md
git commit -m "feat: show home page sections as color-accented icon cards"
```

---

### Task 3: Weather hero card on the home page

**Goal:** Show the weather from `fetch_weather()` as a hero card at the top of the home page — colored condition icon, big temperature, condition, today's high/low and place, with a condition-colored stripe — falling back to a short "Weather unavailable" card when weather can't be fetched.

**Files:**
- Modify: `app/dashboard.py` (pass `fetch_weather()` to the template)
- Create: `templates/_weather_icons.html`
- Modify: `templates/dashboard.html` (full rewrite to the final version)
- Create: `tests/conftest.py`
- Modify: `tests/test_dashboard.py` (imports, sample weather, four new tests)
- Modify: `README.md` (Features bullet, Dashboard Home paragraph, API Usage and Caching section, Kindle Colorsoft Browser Notes bullet)
- Modify: `CLAUDE.md:25` (`/` route row) and the Gotchas list

**Acceptance Criteria:**
- [ ] `GET /` passes `fetch_weather()` to the template; the hero card is the first element on the page (no "Home" heading) and shows the temperature, the condition, and "H x° · L y° · place", with stripe class `wx-<icon>`
- [ ] When `fetch_weather()` returns `None`, the page returns 200 with "Weather unavailable" and all four section cards
- [ ] `weather_icon(name)` renders an `<svg` for every icon name `app/weather.py` can produce, including `night`
- [ ] `tests/conftest.py` stubs `app.dashboard.fetch_weather`, so no test calls Open-Meteo
- [ ] Screenshots of the light, dark, and fallback home pages and the icon sheet were captured and read, and the Step 8 checklist holds
- [ ] README (Features, Dashboard Home, caching, Colorsoft note) and CLAUDE.md (route row, gotcha) are updated
- [ ] `uv run pytest` passes

**Verify:** `uv run pytest tests/test_dashboard.py -v && uv run pytest` → 9 passed in `tests/test_dashboard.py`, then the whole suite passes

**Steps:**

- [ ] **Step 1: Set up the test environment (skip if `.venv/` already exists)**

```bash
[ -d .venv ] || (uv venv && uv pip install -r requirements.txt -r requirements-dev.txt)
```

- [ ] **Step 2: Write the failing tests**

In `tests/test_dashboard.py`, replace the import block at the top with:

```python
"""Tests for the home page."""
from pathlib import Path
from unittest.mock import patch

import pytest

from app import create_app
from app import dashboard as dashboard_module
from app import weather
```

Add this constant directly after `SECTION_CARDS`:

```python
# What fetch_weather() returns on a good day
SAMPLE_WEATHER = {
    "temp": 72,
    "high": 78,
    "low": 55,
    "condition": "Partly cloudy",
    "icon": "partly",
    "location": "San Angelo",
}
```

Add this helper directly after `_home_html`:

```python
def _home_with_weather(client, weather_data):
    """GET the home page with fetch_weather() stubbed to return weather_data."""
    with patch.object(dashboard_module, "fetch_weather", return_value=weather_data):
        return _home_html(client)
```

Append these tests at the end of the file:

```python
def test_weather_card_shows_current_conditions(client):
    html = _home_with_weather(client, SAMPLE_WEATHER)
    assert 'class="weather-card wx-partly"' in html
    assert '<div class="weather-temp">72°</div>' in html
    assert "Partly cloudy" in html
    assert "H 78° · L 55° · San Angelo" in html


def test_weather_card_comes_first_with_no_heading_above_it(client):
    html = _home_with_weather(client, SAMPLE_WEATHER)
    assert html.index('class="weather-card') < html.index('class="dashboard-card')
    assert "dashboard-title" not in html


def test_weather_unavailable_still_renders_home(client):
    html = _home_with_weather(client, None)
    assert 'class="weather-card weather-card-empty"' in html
    assert "Weather unavailable" in html
    for _, _, href in SECTION_CARDS:
        assert f'href="{href}"' in html


def test_every_weather_icon_has_an_svg():
    flask_app = create_app({"TESTING": True})
    with flask_app.app_context():
        weather_icon = flask_app.jinja_env.get_template("_weather_icons.html").module.weather_icon
        names = {icon for _, icon in weather.WMO_CODES.values()} | {"night"}
        for name in sorted(names):
            assert "<svg" in str(weather_icon(name)), f"no SVG for weather icon {name!r}"
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_dashboard.py -v`
Expected: 4 failed, 5 passed — the three weather-card tests fail with `AttributeError: <module 'app.dashboard' …> does not have the attribute 'fetch_weather'`, and `test_every_weather_icon_has_an_svg` fails with `jinja2.exceptions.TemplateNotFound: _weather_icons.html`.

- [ ] **Step 4: Pass the weather to the template and keep tests offline**

Replace the whole of `app/dashboard.py` with:

```python
from flask import Blueprint, render_template

from app.weather import fetch_weather

dashboard_bp = Blueprint("dashboard_bp", __name__)


@dashboard_bp.route("/")
def index() -> str:
    """Render the home page: weather hero card (or its fallback) above the section cards."""
    return render_template("dashboard.html", weather=fetch_weather())
```

Create `tests/conftest.py`:

```python
"""Shared pytest fixtures."""
import pytest


@pytest.fixture(autouse=True)
def offline_weather(monkeypatch):
    """Stub the home page's weather lookup so no test calls Open-Meteo; a test can patch it again to show weather."""
    monkeypatch.setattr("app.dashboard.fetch_weather", lambda: None)
```

- [ ] **Step 5: Add the weather icons macro**

Create `templates/_weather_icons.html`:

```html
{#- Colored weather icons for the home page hero card, one per icon name produced by app/weather.py -#}
{% macro weather_icon(name) -%}
{%- if name == "clear" -%}
{#- Sun: amber disc with eight rays -#}
<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false"><path d="M32 4v8M32 52v8M4 32h8M52 32h8M12.2 12.2l5.7 5.7M46.1 46.1l5.7 5.7M12.2 51.8l5.7-5.7M46.1 17.9l5.7-5.7" stroke="#ffa000" stroke-width="4" stroke-linecap="round"/><circle cx="32" cy="32" r="13" fill="#ffa000"/></svg>
{%- elif name == "night" -%}
{#- Moon: indigo crescent -#}
<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false"><path d="M44 8a24 24 0 1 0 12 36A20 20 0 0 1 44 8z" fill="#5c6bc0"/></svg>
{%- elif name == "partly" -%}
{#- Partly cloudy: amber sun behind a gray cloud -#}
<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false"><circle cx="22" cy="22" r="12" fill="#ffa000"/><path d="M24 52h26a10 10 0 0 0 1-20a14 14 0 0 0-27 2a9 9 0 0 0 0 18z" fill="#90a4ae"/></svg>
{%- elif name == "cloudy" -%}
{#- Overcast: one gray cloud -#}
<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false"><path d="M20 48h26a10 10 0 0 0 1-20a14 14 0 0 0-27 2a9 9 0 0 0 0 18z" fill="#90a4ae"/></svg>
{%- elif name == "fog" -%}
{#- Fog: three gray bars -#}
<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false"><path d="M10 22h44M16 32h38M10 42h44" stroke="#90a4ae" stroke-width="5" stroke-linecap="round"/></svg>
{%- elif name == "rain" -%}
{#- Rain: gray cloud with blue streaks -#}
<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false"><path d="M20 38h26a10 10 0 0 0 1-20a14 14 0 0 0-27 2a9 9 0 0 0 0 18z" fill="#90a4ae"/><path d="M24 44l-4 12M34 44l-4 12M44 44l-4 12" stroke="#1e88e5" stroke-width="4" stroke-linecap="round"/></svg>
{%- elif name == "snow" -%}
{#- Snow: gray cloud with light-blue flakes -#}
<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false"><path d="M20 38h26a10 10 0 0 0 1-20a14 14 0 0 0-27 2a9 9 0 0 0 0 18z" fill="#90a4ae"/><g fill="#039be5"><circle cx="22" cy="46" r="3.5"/><circle cx="34" cy="46" r="3.5"/><circle cx="46" cy="46" r="3.5"/><circle cx="28" cy="56" r="3.5"/><circle cx="40" cy="56" r="3.5"/></g></svg>
{%- elif name == "storm" -%}
{#- Thunderstorm: gray cloud with an amber lightning bolt -#}
<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false"><path d="M20 38h26a10 10 0 0 0 1-20a14 14 0 0 0-27 2a9 9 0 0 0 0 18z" fill="#90a4ae"/><path d="M34 34l-8 14h8l-4 14 12-18h-8l4-10z" fill="#ffa000"/></svg>
{%- endif -%}
{%- endmacro %}
```

The macro has no `else` branch on purpose: an icon name without a drawing renders nothing, and `test_every_weather_icon_has_an_svg` catches it.

- [ ] **Step 6: Add the hero card to the home page**

Replace the whole of `templates/dashboard.html` with:

```html
{% extends "base.html" %}

{% block title %}Home{% endblock %}

{% block styles %}
<style>
    /* Home page column: fills the screen so the Settings card can sit at the bottom */
    .dashboard-menu {
        display: flex;
        flex-direction: column;
        min-height: calc(100vh - 24px);
        margin: 0;
    }
    /* Weather hero card: colored icon left, big temperature right, stripe colored by condition */
    .weather-card {
        display: flex;
        align-items: center;
        padding: 16px;
        margin: 0 0 16px 0;
        border: 2px solid #000;
        border-left: 10px solid #90a4ae;
        border-radius: 12px;
        background: #fff;
        color: #000;
    }
    /* Square box for the weather icon; the SVG scales to fill it */
    .weather-icon {
        flex: 0 0 88px;
        width: 88px;
        height: 88px;
        margin-right: 16px;
    }
    .weather-icon svg {
        display: block;
        width: 100%;
        height: 100%;
    }
    /* Current temperature */
    .weather-temp {
        font-size: 56px;
        line-height: 1;
        font-weight: 700;
    }
    /* Condition label, e.g. "Partly cloudy" */
    .weather-condition {
        margin-top: 4px;
        font-size: 22px;
        line-height: 1.3;
        font-weight: 700;
    }
    /* Today's high / low and the place name */
    .weather-meta {
        font-size: 16px;
        line-height: 1.3;
    }
    /* Fallback text when weather can't be fetched */
    .weather-empty {
        font-size: 18px;
        font-weight: 700;
    }
    /* Weather stripe color per condition (cloudy, fog, and unavailable keep the gray default) */
    .wx-clear, .wx-partly, .wx-storm { border-left-color: #ffa000; }
    .wx-night { border-left-color: #5c6bc0; }
    .wx-rain { border-left-color: #1e88e5; }
    .wx-snow { border-left-color: #039be5; }
    /* Section card: colored left stripe, colored icon tile, black/white text */
    .dashboard-card {
        display: flex;
        align-items: center;
        min-height: 72px;
        padding: 10px 14px;
        margin: 0 0 12px 0;
        border: 2px solid #000;
        border-left: 10px solid #000;
        border-radius: 12px;
        background: #fff;
        color: #000;
        text-decoration: none;
    }
    /* Square colored tile holding the white line icon */
    .dashboard-card-icon {
        flex: 0 0 48px;
        width: 48px;
        height: 48px;
        margin-right: 14px;
        padding: 10px;
        border-radius: 10px;
        color: #fff;
    }
    .dashboard-card-icon svg {
        display: block;
        width: 100%;
        height: 100%;
    }
    /* Card title */
    .dashboard-card-title {
        display: block;
        font-size: 22px;
        line-height: 1.2;
        font-weight: 700;
    }
    /* One-line description under the title */
    .dashboard-card-sub {
        display: block;
        font-size: 15px;
        line-height: 1.3;
    }
    /* Per-section accent: stripe and icon tile share one color */
    .card-reader { border-left-color: #1565c0; }
    .card-reader .dashboard-card-icon { background: #1565c0; }
    .card-highlights { border-left-color: #ef6c00; }
    .card-highlights .dashboard-card-icon { background: #ef6c00; }
    .card-notebook { border-left-color: #2e7d32; }
    .card-notebook .dashboard-card-icon { background: #2e7d32; }
    .card-settings { border-left-color: #546e7a; }
    .card-settings .dashboard-card-icon { background: #546e7a; }
    /* Settings card: pushed to the bottom of the screen */
    .dashboard-settings-link {
        margin-top: auto;
        margin-bottom: 0;
    }
    /* Dark theme: flip text and background; recolor only the plain borders so colored stripes stay */
    body.theme-dark .weather-card,
    body.theme-dark .dashboard-card {
        background: #000;
        color: #fff;
        border-top-color: #fff;
        border-right-color: #fff;
        border-bottom-color: #fff;
    }
</style>
{% endblock %}

{# Empty nav: the weather card is the top of the page, replacing the heading and base.html's Home button #}
{% block nav %}{% endblock %}

{% block content %}
{% from "_weather_icons.html" import weather_icon %}
<main class="dashboard-menu">
    {# Weather hero card: live conditions, or a short notice when weather can't be fetched #}
    {% if weather %}
    <section class="weather-card wx-{{ weather.icon }}" aria-label="Weather">
        <div class="weather-icon">{{ weather_icon(weather.icon) }}</div>
        <div class="weather-body">
            <div class="weather-temp">{{ weather.temp }}°</div>
            <div class="weather-condition">{{ weather.condition }}</div>
            <div class="weather-meta">H {{ weather.high }}° · L {{ weather.low }}° · {{ weather.location }}</div>
        </div>
    </section>
    {% else %}
    <section class="weather-card weather-card-empty" aria-label="Weather">
        <p class="weather-empty">Weather unavailable</p>
    </section>
    {% endif %}
    {# Section cards: one per tool, each with its own accent color and icon #}
    <a class="dashboard-card card-reader" href="{{ url_for('reader_bp.article_list') }}">
        <span class="dashboard-card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z"/><path d="M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z"/></svg></span>
        <span class="dashboard-card-text">
            <span class="dashboard-card-title">Reader</span>
            <span class="dashboard-card-sub">Shortlist and Later</span>
        </span>
    </a>
    <a class="dashboard-card card-highlights" href="{{ url_for('highlights_bp.daily_review') }}">
        <span class="dashboard-card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 013 3L7 19l-4 1 1-4z"/></svg></span>
        <span class="dashboard-card-text">
            <span class="dashboard-card-title">Highlights</span>
            <span class="dashboard-card-sub">Daily Review</span>
        </span>
    </a>
    <a class="dashboard-card card-notebook" href="{{ url_for('notebook_bp.index') }}">
        <span class="dashboard-card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M16 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V8z"/><path d="M15 3v5h6"/><path d="M7 13h10M7 17h6"/></svg></span>
        <span class="dashboard-card-text">
            <span class="dashboard-card-title">Notebook</span>
            <span class="dashboard-card-sub">Journal and to-dos</span>
        </span>
    </a>
    {# Settings stays reachable, pinned to the bottom of the screen #}
    <a class="dashboard-card card-settings dashboard-settings-link" href="{{ url_for('settings_bp.settings') }}">
        <span class="dashboard-card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/></svg></span>
        <span class="dashboard-card-text">
            <span class="dashboard-card-title">Settings</span>
            <span class="dashboard-card-sub">Theme, text, and sorting</span>
        </span>
    </a>
</main>
{% endblock %}
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `uv run pytest tests/test_dashboard.py -v`
Expected: 9 passed

Run: `uv run pytest`
Expected: all tests pass (the autouse stub keeps `test_auto_theme_adds_auto_body_class` and every other `GET /` offline)

- [ ] **Step 8: Screenshot the hero card and icons, and read the screenshots**

The home page has no JS or external assets, so its server-rendered HTML saved to a static file looks exactly like the live page; a fixed sample weather makes the shot repeatable. `.codex-screenshots/` is gitignored, so nothing written there gets committed.

Render the pages and an icon sheet:

```bash
mkdir -p .codex-screenshots
cat > .codex-screenshots/render_home.py <<'EOF'
"""Save server-rendered home pages and a weather-icon sheet as static HTML for screenshot checks (scratch; never committed)."""
from pathlib import Path
from unittest.mock import patch

from app import create_app, dashboard, weather

OUT = Path(".codex-screenshots")
SAMPLE = {"temp": 72, "high": 78, "low": 55, "condition": "Partly cloudy", "icon": "partly", "location": "San Angelo"}
app = create_app({"TESTING": True})
client = app.test_client()

# Home page with sample weather in each theme, plus the weather-unavailable fallback
for name, theme, wx in (("home-light", "light", SAMPLE), ("home-dark", "dark", SAMPLE), ("home-noweather", "light", None)):
    client.set_cookie("readwise_theme", theme)
    with patch.object(dashboard, "fetch_weather", return_value=wx):
        (OUT / f"{name}.html").write_text(client.get("/").get_data(as_text=True), encoding="utf-8")

# Every weather icon, once on a white strip and once on a black strip
with app.app_context():
    icon = app.jinja_env.get_template("_weather_icons.html").module.weather_icon
    names = sorted({i for _, i in weather.WMO_CODES.values()} | {"night"})
    cells = "".join(f'<figure><div class="i">{icon(n)}</div><figcaption>{n}</figcaption></figure>' for n in names)
style = "<style>figure{display:inline-block;margin:8px;text-align:center;font-family:Georgia,serif}.i svg{width:88px;height:88px}.s{padding:8px}</style>"
page = f'<!DOCTYPE html><meta charset="utf-8">{style}<div class="s" style="background:#fff;color:#000">{cells}</div><div class="s" style="background:#000;color:#fff">{cells}</div>'
(OUT / "icon-sheet.html").write_text(page, encoding="utf-8")
EOF
PYTHONPATH=. uv run python .codex-screenshots/render_home.py && ls .codex-screenshots
```

Expected: `home-dark.html  home-light.html  home-noweather.html  icon-sheet.html  render_home.py`

Serve the folder on port 5557 (5555 belongs to the Docker container). Create `.claude/launch.json` if it doesn't exist (local tooling — don't commit it; if it exists without a `home-shots` entry, add the entry by hand):

```bash
mkdir -p .claude && [ -f .claude/launch.json ] || cat > .claude/launch.json <<EOF
{"version": "0.0.1", "configurations": [{"name": "home-shots", "runtimeExecutable": "python3", "runtimeArgs": ["-m", "http.server", "5557", "--bind", "127.0.0.1", "--directory", "$PWD/.codex-screenshots"], "port": 5557}]}
EOF
```

Then, with the Browser pane tools (`mcp__Claude_Browser__*`):
1. `preview_start` with name `home-shots`. If it can't find that config, run `python3 -m http.server 5557 --bind 127.0.0.1 --directory "$PWD/.codex-screenshots"` with Bash `run_in_background` and call `preview_start` with url `http://127.0.0.1:5557/home-light.html`.
2. `resize_window` width 632, height 840.
3. For each of `home-light.html`, `home-dark.html`, `home-noweather.html`, `icon-sheet.html`: `navigate` to `http://127.0.0.1:5557/<file>` → `computer` action `screenshot`.
4. `resize_window` preset `desktop`, then `preview_stop` (or stop the background server).

Read each screenshot and confirm:
- `home-light`: the weather card is the first thing on the page (no "Home" heading above it), with an amber left stripe, the sun-behind-cloud icon on the left, a large bold "72°", "Partly cloudy", and "H 78° · L 55° · San Angelo"; the four section cards follow, with Settings at the bottom.
- `home-dark`: same layout with white text and white top/right/bottom borders on black; the stripe and icon colors are unchanged.
- `home-noweather`: a short card with a gray stripe reading "Weather unavailable", then the four section cards.
- `icon-sheet`: eight distinct, recognizable icons on both strips (clear = sun, cloudy, fog, night = moon, partly, rain, snow, storm); nothing clipped at the box edges.

If anything is off, fix the CSS or SVG, re-run the render script, re-take the screenshots, and re-run `uv run pytest`. If the Browser pane tools aren't available to you, don't skip this step: report it as blocked so the coordinator runs it.

- [ ] **Step 9: Update the README and CLAUDE.md**

In `README.md`:

Replace the Features bullet

```markdown
- **Dashboard home** at `/` with a color-coded card and icon for each tool.
```

with

```markdown
- **Dashboard home** at `/` with a weather card and a color-coded card and icon for each tool.
```

Replace the paragraph under `### Dashboard Home` with:

```markdown
Open `/` for the launch point into the dashboard features. A weather card at the top shows the current temperature, conditions, and today's high/low for the place set by `WEATHER_LAT`, `WEATHER_LON`, and `WEATHER_LOCATION` (San Angelo, TX by default). If the weather can't be fetched, the card says "Weather unavailable" and the rest of the page works normally. Below it, Reader, Highlights, and Notebook each get a card with its own accent color and icon; Settings sits at the bottom of the screen.
```

At the end of the `## API Usage and Caching` section (after the `If a 429 is returned …` paragraph), add:

```markdown
Home page weather comes from [Open-Meteo](https://open-meteo.com/) (free, no API key) and is cached for 30 minutes in the same disk cache. Failed lookups aren't cached, so the next page load tries again; each attempt waits at most 5 seconds.
```

In `## Kindle Colorsoft Browser Notes`, replace the last bullet (`- The Colorsoft has a Kaleido 3 color layer, but the UI stays deliberately monochrome/high-contrast …`) with:

```markdown
- The Colorsoft has a Kaleido 3 color layer, but it runs at 150 ppi vs. 300 ppi for black-and-white, so text always stays black (light theme) or white (dark theme). Reading views stay fully monochrome; the home page uses bold color only as accents — card stripes, icon tiles, and weather icons.
```

In `CLAUDE.md`, replace the `/` row of the Architecture table

```markdown
| `/` | `app/dashboard.py` — home page |
```

with

```markdown
| `/` | `app/dashboard.py` — home page (weather hero card data from `app/weather.py`) |
```

and add this bullet to `## Gotchas`, directly before `- No linter, formatter, or CI is configured for this project.`:

```markdown
- The home page calls Open-Meteo through `app/weather.py` (no API key; cached 30 min under `weather:<lat>:<lon>`; location from `WEATHER_LAT` / `WEATHER_LON` / `WEATHER_LOCATION`). Any failure makes `fetch_weather()` return `None` and the page shows "Weather unavailable". `tests/conftest.py` stubs `app.dashboard.fetch_weather` to `None` for every test so the suite stays offline — patch it inside a test to render a weather card.
```

- [ ] **Step 10: Commit**

```bash
git add app/dashboard.py templates/_weather_icons.html templates/dashboard.html tests/conftest.py tests/test_dashboard.py README.md CLAUDE.md
git commit -m "feat: add weather hero card to the home page"
```
