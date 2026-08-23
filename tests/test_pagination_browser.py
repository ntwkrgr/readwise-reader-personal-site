"""Browser-level regression test for tap-to-advance pagination.

`_paginate.html` snaps page boundaries to real line-box positions measured in the
DOM. `tests/test_routes.py` only asserts the paginator script is present in the
response; it can't catch a boundary that's off by a few pixels. This test renders
the actual reading view in headless Chromium, scrolls to every boundary the
pagination script computes, and asserts nothing is painted below the viewport
bottom on any page.

Requires Playwright's Chromium to be installed (`playwright install chromium`).
Skips cleanly if the driver or browser isn't available, so it never blocks a
plain `uv run pytest` in an environment without a browser.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

import diskcache
import pytest

from app import cache as cache_module
from app import create_app
from app.reader import routes as routes_module

playwright_sync_api = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright_sync_api.sync_playwright

try:
    with sync_playwright() as _p:
        _p.chromium.launch().close()
    CHROMIUM_AVAILABLE = True
except Exception:
    CHROMIUM_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not CHROMIUM_AVAILABLE,
    reason="Playwright Chromium not installed (run `playwright install chromium`)",
)


# --- Fixture content exercising every layout case that can paint outside a text rect ---

_LONG_PARAGRAPH = (
    "The quick brown fox jumps over the lazy dog near the riverbank while the "
    "autumn wind carries the scent of fallen leaves across the quiet meadow, "
    "and travelers pause to watch the sun dip below the distant hills before "
    "continuing their long journey home through the winding forest trail."
)

ARTICLE_HTML = "".join(
    [
        f"<p>{_LONG_PARAGRAPH} {_LONG_PARAGRAPH}</p>",
        f"<p>{_LONG_PARAGRAPH}</p>",
        "<h2>A Heading With Different Line Height</h2>",
        f"<p>{_LONG_PARAGRAPH} {_LONG_PARAGRAPH}</p>",
        "<ul>"
        + "".join(f"<li>List item number {i} with some wrapping text content here.</li>" for i in range(1, 5))
        + "</ul>",
        "<ol>"
        + "".join(f"<li>Ordered item {i} with a bit of extra text to wrap the line.</li>" for i in range(1, 4))
        + "</ol>",
        f"<blockquote>{_LONG_PARAGRAPH}</blockquote>",
        "<hr>",
        f"<p>{_LONG_PARAGRAPH} {_LONG_PARAGRAPH}</p>",
        "<table><tr><th>Col A</th><th>Col B</th></tr>"
        "<tr><td>Value one</td><td>Value two</td></tr>"
        "<tr><td>Value three</td><td>Value four</td></tr></table>",
        "<pre>def example():\n    return 42\n\nfor i in range(3):\n    print(i)</pre>",
        f'<p style="border-bottom: 3px solid;">{_LONG_PARAGRAPH}</p>',
        f"<p>{_LONG_PARAGRAPH} {_LONG_PARAGRAPH}</p>" * 3,
    ]
)

SAMPLE_ARTICLE: dict[str, Any] = {
    "id": "abc123",
    "title": "Pagination Fixture Article",
    "author": "Test Author",
    "word_count": 2000,
    "reading_time": "10 min",
    "reading_progress": 0.0,
    "tags": {},
    "saved_at": "2024-01-01T00:00:00Z",
    "created_at": "2024-01-01T00:00:00Z",
    "location": "later",
    "category": "article",
    "parent_id": None,
    "html_content": ARTICLE_HTML,
    "source_url": "https://example.com/article",
}


@pytest.fixture
def client(tmp_path):
    flask_app = create_app({"TESTING": True})
    cache = diskcache.Cache(str(tmp_path / "cache"))
    with patch.object(cache_module, "_cache", cache):
        with flask_app.test_client() as c:
            yield c
    cache.close()


def render_reading_view(client, *, text_size: str, theme: str) -> str:
    client.set_cookie("readwise_tap_advance", "on")
    client.set_cookie("readwise_text_size", text_size)
    client.set_cookie("readwise_theme", theme)
    with patch.object(routes_module, "fetch_article", return_value=SAMPLE_ARTICLE):
        resp = client.get("/reader/read/abc123")
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


# --- In-page oracle: find any painted rect straddling a page boundary ---

_ORACLE_JS = """
() => {
    var dbg = window.__readerPaginationDebug;
    if (!dbg) return { error: 'no debug hook found on window' };

    var article = document.getElementById('article-content');
    var starts = dbg.getStarts();
    var EPS = 0.5;
    var pages = [];

    function findStraddlers(boundary) {
        var straddlers = [];

        function checkRect(rect, label) {
            if (!rect || rect.height <= 0) return;
            if (rect.top < boundary - EPS && rect.bottom > boundary + EPS) {
                straddlers.push({
                    label: label,
                    top: Math.round(rect.top * 100) / 100,
                    bottom: Math.round(rect.bottom * 100) / 100,
                    overflow: Math.round((rect.bottom - boundary) * 100) / 100
                });
            }
        }

        // 1. Every rendered text line.
        var walker = document.createTreeWalker(article, NodeFilter.SHOW_TEXT, null, false);
        var node;
        var range = document.createRange();
        while ((node = walker.nextNode())) {
            if (!node.nodeValue || !/\\S/.test(node.nodeValue)) continue;
            range.selectNodeContents(node);
            var rects = range.getClientRects();
            for (var i = 0; i < rects.length; i++) {
                checkRect(rects[i], 'text:' + node.nodeValue.trim().slice(0, 30));
            }
        }

        // 2. Leaf elements with no text of their own (hr, stripped-img placeholders, etc).
        //    Excludes aria-hidden elements: those are the pagination script's own
        //    invisible layout spacers, not reader-visible content.
        var all = article.querySelectorAll('*');
        var j, el;
        for (j = 0; j < all.length; j++) {
            el = all[j];
            if (el.getAttribute('aria-hidden') === 'true') continue;
            if (el.children.length === 0 && !/\\S/.test(el.textContent || '')) {
                checkRect(el.getBoundingClientRect(), 'leaf:' + el.tagName);
            }
        }

        // 3. Decorative borders/backgrounds painted past the text (borders, table cell
        //    backgrounds, source-HTML inline styles) - independent of text-rect coverage.
        for (j = 0; j < all.length; j++) {
            el = all[j];
            if (el.getAttribute('aria-hidden') === 'true') continue;
            var cs = window.getComputedStyle(el);
            var hasBorder = parseFloat(cs.borderBottomWidth) > 0 && cs.borderBottomStyle !== 'none';
            var bg = cs.backgroundColor;
            var hasBg = bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent';
            if (!hasBorder && !hasBg) continue;
            var r = el.getBoundingClientRect();
            if (hasBorder) {
                checkRect({ top: r.bottom - 1, bottom: r.bottom, height: 1 }, 'border-bottom:' + el.tagName);
            }
            if (hasBg) {
                checkRect(r, 'background:' + el.tagName);
            }
        }

        return straddlers;
    }

    for (var i = 0; i < starts.length; i++) {
        window.scrollTo(0, starts[i]);
        var clientHeight = document.documentElement.clientHeight;
        pages.push({
            index: i,
            start: starts[i],
            clientHeight: clientHeight,
            innerHeight: window.innerHeight,
            pageH: dbg.getPageH(),
            straddlers: findStraddlers(clientHeight)
        });
    }

    return { pages: pages, pageCount: starts.length };
}
"""


@pytest.mark.parametrize("text_size", ["small", "medium", "large"])
@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("viewport_height", [500, 700, 900])
def test_no_line_straddles_a_page_boundary(client, text_size, theme, viewport_height):
    html = render_reading_view(client, text_size=text_size, theme=theme)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 800, "height": viewport_height})
        page.set_content(html, wait_until="load")
        result = page.evaluate(_ORACLE_JS)
        browser.close()

    assert "error" not in result, result.get("error")
    assert result["pageCount"] > 1, "fixture content did not produce multiple pages"

    failures = []
    for p_info in result["pages"]:
        if p_info["straddlers"]:
            failures.append(p_info)

    if failures:
        lines = [
            f"text_size={text_size} theme={theme} viewport_height={viewport_height}: "
            f"{len(failures)}/{result['pageCount']} pages have straddling content"
        ]
        for p_info in failures:
            lines.append(
                f"  page {p_info['index']}: clientHeight={p_info['clientHeight']} "
                f"innerHeight={p_info['innerHeight']} pageH={p_info['pageH']}"
            )
            for s in p_info["straddlers"]:
                lines.append(
                    f"    STRADDLER {s['label']!r} top={s['top']} bottom={s['bottom']} "
                    f"overflow={s['overflow']}px"
                )
        pytest.fail("\n".join(lines))
