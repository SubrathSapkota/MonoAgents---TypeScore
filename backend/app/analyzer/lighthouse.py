"""
lighthouse.py — HTTP-based performance & font-loading analyzer.
Replaces the Lighthouse CLI dependency with direct HTTP checks that
estimate performance and detect font-loading issues from static analysis.
"""

import asyncio
import re
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.utils.http_client import fetch, fetch_with_timing
from app.utils.http_client import _SESSION as _HTTP_SESSION  # shared session for HEAD requests


# Matches any url(...) value in CSS that ends with a font file extension.
# Handles quoted/unquoted, absolute and relative paths, and query strings.
_FONT_URL_RE = re.compile(
    r"""url\s*\(\s*['"]?((?:https?://|//)?[^'")\s]+\.(?:woff2?|ttf|otf|eot)[^'")\s]*?)['"]?\s*\)""",
    re.IGNORECASE,
)


def check_font_display(css_text: str) -> bool:
    """Return True if @font-face rules include font-display."""
    face_re = re.compile(r"@font-face\s*\{[^}]+\}", re.DOTALL | re.IGNORECASE)
    display_re = re.compile(r"font-display\s*:", re.IGNORECASE)
    for face in face_re.finditer(css_text):
        if not display_re.search(face.group(0)):
            return False  # At least one @font-face missing font-display
    return True


def check_font_file_sizes(css: str, base_url: str, limit: int = 5) -> list[dict]:
    """
    Extract font file URLs from @font-face src declarations and HEAD-request
    each one to measure its Content-Length.

    Returns a list of {"url": str, "size_kb": float} for every font file
    that could be measured.  Files whose size cannot be determined (no
    Content-Length header, network error, data: URIs) are silently skipped.

    Parameters
    ----------
    css      : concatenated CSS text already collected by analyze_url()
    base_url : page origin used to resolve relative URLs
    limit    : maximum number of font files to probe (keeps scan time bounded)
    """
    seen: set[str] = set()
    results: list[dict] = []

    for m in _FONT_URL_RE.finditer(css):
        raw = m.group(1).strip()

        # Skip data URIs — they are inline and have no transfer size
        if raw.startswith("data:"):
            continue

        # Resolve protocol-relative and relative URLs
        if raw.startswith("//"):
            raw = "https:" + raw
        elif not raw.startswith("http"):
            raw = urljoin(base_url, raw)

        if raw in seen:
            continue
        seen.add(raw)

        if len(results) >= limit:
            break

        try:
            resp = _HTTP_SESSION.head(raw, timeout=5, allow_redirects=True)
            content_length = int(resp.headers.get("content-length", 0))
            if content_length > 0:
                results.append({
                    "url": raw,
                    "size_kb": round(content_length / 1024, 1),
                })
        except Exception:
            pass  # network error or unsupported method — skip silently

    return results


async def _get_cwv_browser(url: str) -> dict:
    """
    Launch a headless Chromium browser via Playwright, navigate to the URL,
    and collect real LCP and CLS values using the browser's native
    Performance Observer API.

    Returns {"lcp_ms": int, "cls": float} on success, or
            {"lcp_ms": None, "cls": None} on any failure (import error,
            network block, timeout, Cloudflare, etc.).

    Timeout budget: 15 s for page navigation + 2 s layout-shift settle +
    1 s observer flush = ~18 s worst-case per call.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[cwv] playwright not installed — run: playwright install chromium")
        return {"lcp_ms": None, "cls": None}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=15_000)
            except Exception:
                # networkidle timed out — page still loaded enough for CWV
                pass

            # Wait for layout shifts to settle after initial load
            await page.wait_for_timeout(2_000)

            # Read LCP and CLS from the browser's Performance Observer API.
            # PerformanceObserver with buffered:true replays entries that
            # already happened before the observer was registered.
            cwv: dict = await page.evaluate("""
                () => new Promise(resolve => {
                    const result = { lcp_ms: null, cls: 0.0 };

                    try {
                        new PerformanceObserver(list => {
                            const entries = list.getEntries();
                            if (entries.length) {
                                // Last entry is always the latest LCP candidate
                                result.lcp_ms = entries[entries.length - 1].startTime;
                            }
                        }).observe({ type: 'largest-contentful-paint', buffered: true });
                    } catch(e) {}

                    try {
                        new PerformanceObserver(list => {
                            for (const entry of list.getEntries()) {
                                // Only unexpected shifts count toward CLS
                                if (!entry.hadRecentInput) {
                                    result.cls += entry.value;
                                }
                            }
                        }).observe({ type: 'layout-shift', buffered: true });
                    } catch(e) {}

                    // Give observers 1 s to flush buffered entries
                    setTimeout(() => resolve(result), 1_000);
                })
            """)

            await browser.close()

            lcp = cwv.get("lcp_ms")
            cls = cwv.get("cls", 0.0)
            print(f"[cwv] Browser — LCP={lcp} ms, CLS={round(cls, 3)}")

            return {
                "lcp_ms": round(lcp) if lcp else None,
                "cls": round(float(cls), 3) if cls is not None else None,
            }

    except Exception as e:
        print(f"[cwv] Browser measurement failed: {e}")
        return {"lcp_ms": None, "cls": None}


def estimate_performance_score(
    response_ms: float,
    html_bytes: int,
    css_count: int,
    google_fonts: bool,
    font_display_ok: bool,  # retained for API compat; deduction applied in scoring/performance.py
) -> tuple[int, dict]:
    """
    Heuristic performance score (0-100) plus a breakdown of every deduction.

    Returns
    -------
    (score: int, breakdown: dict)
      breakdown keys: response_time_penalty, html_size_penalty,
                      css_count_penalty, google_fonts_penalty
      (all values are non-negative integers representing points deducted)

    Note: the font-display @font-face deduction (-10) is applied in
    scoring/performance.py so all scoring decisions live in one place.
    """
    score = 100
    breakdown: dict[str, int] = {}

    # Google Fonts loaded without display=swap (request-level blocking issue)
    p = 5 if google_fonts else 0
    score -= p
    breakdown["google_fonts_penalty"] = p

    return max(0, min(100, score)), breakdown


async def analyze_url(url: str) -> dict:
    """
    Main entry point. Returns compact metrics compatible with the scoring engine:
    {
      "performance": 75,
      "lcp_ms": 1200,
      "cls": None,
      "font_warnings": ["Ensure text remains visible during webfont load"]
    }
    """
    if not url.startswith("http"):
        url = "https://" + url

    print(f"[lighthouse] Analyzing {url} …")

    html, response_ms = fetch_with_timing(url)
    if html is None:
        return {
            "performance": None,
            "lcp_ms": None,
            "cls": None,
            "font_warnings": [],
            "error": "Failed to fetch page",
        }

    html_bytes = len(html.encode("utf-8"))
    soup = BeautifulSoup(html, "html.parser")
    font_warnings: list[str] = []

    # Collect CSS files
    css_links = soup.find_all("link", rel=lambda v: v and "stylesheet" in v)
    css_count = len(css_links)

    # Check for Google Fonts without display=swap
    google_fonts = False
    gfonts_display_swap = True
    for link in css_links:
        href = link.get("href", "")
        if "fonts.googleapis.com" in href:
            google_fonts = True
            if "display=swap" not in href:
                gfonts_display_swap = False

    if google_fonts and not gfonts_display_swap:
        font_warnings.append("Ensure text remains visible during webfont load (add display=swap to Google Fonts URL)")

    # Check font-display in custom @font-face rules
    all_css = ""
    for style_tag in soup.find_all("style"):
        all_css += style_tag.get_text() + "\n"

    # Fetch up to 3 CSS files to check @font-face rules
    for link_tag in css_links[:3]:
        href = link_tag.get("href", "")
        if href and "fonts.googleapis.com" not in href:
            abs_href = urljoin(url, href)
            css_text = fetch(abs_href)
            if css_text:
                all_css += css_text + "\n"

    # Check if @font-face rules have font-display
    has_font_face = bool(re.search(r"@font-face", all_css, re.IGNORECASE))
    font_display_ok = True
    if has_font_face:
        font_display_ok = check_font_display(all_css)
        if not font_display_ok:
            font_warnings.append("One or more @font-face declarations are missing font-display property")

    # Check for render-blocking resources
    render_blocking = sum(
        1 for link in css_links
        if not link.get("media") or link.get("media") == "all"
    )
    if render_blocking > 5:
        font_warnings.append(f"{render_blocking} render-blocking stylesheets detected")

    # Check unused/excessive font variants
    font_face_count = len(re.findall(r"@font-face", all_css, re.IGNORECASE))
    if font_face_count > 8:
        font_warnings.append(f"{font_face_count} @font-face declarations — consider subsetting or reducing variants")

    # Check font file sizes via HEAD requests (brief: flag files > 100KB)
    large_font_files = [
        f for f in check_font_file_sizes(all_css, url)
        if f["size_kb"] > 100
    ]
    if large_font_files:
        for f in large_font_files:
            font_warnings.append(
                f"Font file exceeds 100 KB: {f['url'].split('/')[-1].split('?')[0]} "
                f"({f['size_kb']} KB)"
            )

    perf_score, base_breakdown = estimate_performance_score(
        response_ms=response_ms,
        html_bytes=html_bytes,
        css_count=css_count,
        google_fonts=google_fonts and not gfonts_display_swap,
        font_display_ok=font_display_ok,
    )
    # Attach raw measurements so performance.py can write human-readable messages
    base_breakdown["response_ms"] = round(response_ms)
    base_breakdown["html_kb"] = round(html_bytes / 1024)
    base_breakdown["css_count"] = css_count

    # Estimate LCP from response time — used as fallback if browser run fails
    estimated_lcp_ms = round(response_ms * 1.5 + 300)

    # Real LCP + CLS from a headless browser (Playwright).
    # Falls back to the HTTP estimate for LCP and None for CLS if the browser
    # run fails (Cloudflare block, timeout, playwright not installed, etc.)
    print(f"[lighthouse] Launching browser for real CWV measurement …")
    cwv = await _get_cwv_browser(url)
    lcp_ms = cwv["lcp_ms"] if cwv["lcp_ms"] else estimated_lcp_ms
    cls_val = cwv["cls"]  # None if browser failed — CLS deduction stays dormant

    print(f"[lighthouse] Done — performance={perf_score}, "
          f"lcp={lcp_ms}ms ({'browser' if cwv['lcp_ms'] else 'estimated'}), "
          f"cls={cls_val}, "
          f"font warnings={len(font_warnings)}")

    return {
        "performance": perf_score,
        "lcp_ms": lcp_ms,
        "cls": cls_val,
        "font_warnings": font_warnings,
        # Raw signals consumed by scoring/performance.py for explicit deductions
        "font_display_ok": font_display_ok,
        "has_font_face": has_font_face,
        "google_fonts_no_swap": google_fonts and not gfonts_display_swap,
        "render_blocking_count": render_blocking,
        "large_font_files": large_font_files,
        # Base score breakdown — lets performance.py explain deductions in the UI
        "base_score_breakdown": base_breakdown,
    }


if __name__ == "__main__":
    import json
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "https://stripe.com"
    result = asyncio.run(analyze_url(target))
    print(json.dumps(result, indent=2))
