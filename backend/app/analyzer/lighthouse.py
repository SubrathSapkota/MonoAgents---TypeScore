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


def estimate_performance_score(
    response_ms: float,
    html_bytes: int,
    css_count: int,
    google_fonts: bool,
    font_display_ok: bool,  # retained for API compat; deduction now applied in scoring/performance.py
) -> int:
    """
    Heuristic performance score (0-100).
    Deducts points for slow response, heavy HTML, and many CSS files.

    Note: the font-display @font-face deduction (-10) was moved to
    scoring/performance.py so all scoring logic lives in one place.
    The google_fonts (-5) deduction stays here because it represents a
    request-level loading strategy rather than a font-declaration violation.
    """
    score = 100

    # Response time penalty.
    # Threshold starts at 800 ms (not 500 ms) to account for geographic
    # distance between the scanner server and the target site — a well-run
    # site in another region can legitimately take 600–700 ms.
    if response_ms > 3000:
        score -= 30
    elif response_ms > 2000:
        score -= 20
    elif response_ms > 1000:
        score -= 10
    elif response_ms > 800:
        score -= 5

    # HTML size penalty (over 100KB is heavy)
    if html_bytes > 500_000:
        score -= 15
    elif html_bytes > 200_000:
        score -= 10
    elif html_bytes > 100_000:
        score -= 5

    # Too many CSS files = render-blocking risk.
    # Threshold raised from 5 to 10 — modern apps using code-splitting or
    # component libraries commonly ship 6–10 CSS chunks by design.
    if css_count > 15:
        score -= 10
    elif css_count > 10:
        score -= 5

    # Google Fonts loaded without display=swap is a request-level blocking issue
    if google_fonts:
        score -= 5

    # font-display @font-face deduction intentionally removed from here —
    # it is now applied in scoring/performance.py to keep scoring logic centralised.

    return max(0, min(100, score))


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

    perf_score = estimate_performance_score(
        response_ms=response_ms,
        html_bytes=html_bytes,
        css_count=css_count,
        google_fonts=google_fonts and not gfonts_display_swap,
        font_display_ok=font_display_ok,
    )

    # Estimate LCP from response time (rough proxy)
    estimated_lcp_ms = round(response_ms * 1.5 + 300)

    print(f"[lighthouse] Done — performance={perf_score}, "
          f"estimated_lcp={estimated_lcp_ms}ms, "
          f"font warnings={len(font_warnings)}")

    return {
        "performance": perf_score,
        "lcp_ms": estimated_lcp_ms,
        "cls": None,  # Not measurable without a real browser
        "font_warnings": font_warnings,
        # Raw signals consumed by scoring/performance.py for explicit deductions
        "font_display_ok": font_display_ok,
        "has_font_face": has_font_face,
        "google_fonts_no_swap": google_fonts and not gfonts_display_swap,
        "render_blocking_count": render_blocking,
        "large_font_files": large_font_files,  # list[{"url": str, "size_kb": float}]
    }


if __name__ == "__main__":
    import json
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "https://stripe.com"
    result = asyncio.run(analyze_url(target))
    print(json.dumps(result, indent=2))
