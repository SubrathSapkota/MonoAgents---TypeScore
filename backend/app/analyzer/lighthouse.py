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


def check_font_display(css_text: str) -> bool:
    """Return True if @font-face rules include font-display."""
    face_re = re.compile(r"@font-face\s*\{[^}]+\}", re.DOTALL | re.IGNORECASE)
    display_re = re.compile(r"font-display\s*:", re.IGNORECASE)
    for face in face_re.finditer(css_text):
        if not display_re.search(face.group(0)):
            return False  # At least one @font-face missing font-display
    return True


def estimate_performance_score(
    response_ms: float,
    html_bytes: int,
    css_count: int,
    google_fonts: bool,
    font_display_ok: bool,
) -> int:
    """
    Heuristic performance score (0-100).
    Deducts points for slow response, heavy HTML, many CSS files, blocking fonts.
    """
    score = 100

    # Response time penalty
    if response_ms > 3000:
        score -= 30
    elif response_ms > 2000:
        score -= 20
    elif response_ms > 1000:
        score -= 10
    elif response_ms > 500:
        score -= 5

    # HTML size penalty (over 100KB is heavy)
    if html_bytes > 500_000:
        score -= 15
    elif html_bytes > 200_000:
        score -= 10
    elif html_bytes > 100_000:
        score -= 5

    # Too many CSS files = render-blocking risk
    if css_count > 10:
        score -= 10
    elif css_count > 5:
        score -= 5

    # Google Fonts loaded without display=swap is blocking
    if google_fonts:
        score -= 5

    # Missing font-display in @font-face
    if not font_display_ok:
        score -= 10

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
        "cls": None,  # Not measurable without a browser
        "font_warnings": font_warnings,
    }


if __name__ == "__main__":
    import json
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "https://stripe.com"
    result = asyncio.run(analyze_url(target))
    print(json.dumps(result, indent=2))
