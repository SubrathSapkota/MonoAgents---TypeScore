"""
extractor/crawler.py — BFS page discovery using Playwright.

Ported from crawler.js. Discovers same-origin pages starting from one URL
using a breadth-first crawl bounded by max_pages and max_depth.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, urljoin


SKIP_EXT_RE = re.compile(
    r"\.(pdf|zip|png|jpe?g|gif|svg|webp|mp4|mp3|css|js|ico|woff2?|ttf|eot)(\?|$)",
    re.IGNORECASE,
)


def normalize_url(url: str) -> str | None:
    """Normalize URL: strip hash, trailing slash (except root)."""
    try:
        parsed = urlparse(url)
        path = parsed.path
        if len(path) > 1 and path.endswith("/"):
            path = path.rstrip("/")
        normalized = parsed._replace(fragment="", path=path).geturl()
        return normalized
    except Exception:
        return None


async def crawl(browser, start_url: str, *, max_pages: int = 5, max_depth: int = 1, delay_ms: int = 300) -> list[str]:
    """
    BFS crawl from start_url, collecting same-origin internal links.

    Parameters
    ----------
    browser   : Playwright browser instance
    start_url : Starting URL
    max_pages : Maximum number of pages to discover
    max_depth : Maximum link depth from the start URL
    delay_ms  : Polite delay between page loads

    Returns
    -------
    List of discovered same-origin URLs (up to max_pages)
    """
    start = normalize_url(start_url)
    if not start:
        raise ValueError(f"Invalid start URL: {start_url}")

    origin = f"{urlparse(start).scheme}://{urlparse(start).netloc}"

    found = [start]
    seen = {start}
    queue = [(start, 0)]

    page = await browser.new_page()
    try:
        while queue and len(found) < max_pages:
            url, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                links = await page.eval_on_selector_all(
                    "a[href]",
                    "elements => elements.map(a => a.href)"
                )
            except Exception:
                continue

            for raw in links:
                n = normalize_url(raw)
                if not n or n in seen:
                    continue
                parsed = urlparse(n)
                link_origin = f"{parsed.scheme}://{parsed.netloc}"
                if link_origin != origin:
                    continue
                if SKIP_EXT_RE.search(n):
                    continue

                seen.add(n)
                found.append(n)
                queue.append((n, depth + 1))
                if len(found) >= max_pages:
                    break

            if delay_ms:
                await page.wait_for_timeout(delay_ms)
    finally:
        await page.close()

    return found[:max_pages]
