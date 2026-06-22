"""
scanner.py — HTTP-based website font & style scanner
Fetches pages with requests, parses CSS files and inline styles with BeautifulSoup
to extract font-family declarations. No browser required.

Key feature: distinguishes PRIMARY fonts (first in a font-family stack, the
intentional brand choice) from FALLBACK fonts (2nd+ position, safety nets).
"""

import asyncio
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.utils.http_client import fetch


# ─── Font extraction ───────────────────────────────────────────────────────────

# Matches: font-family: "Inter", Arial, sans-serif;
FONT_FAMILY_RE = re.compile(
    r"font-family\s*:\s*([^;}{]+)",
    re.IGNORECASE,
)

# Matches @font-face { font-family: "MyFont"; ... }
FONT_FACE_NAME_RE = re.compile(
    r"@font-face\s*\{[^}]*font-family\s*:\s*['\"]?([^'\";\}]+)['\"]?",
    re.IGNORECASE | re.DOTALL,
)

# Matches Google Fonts family= param: ?family=Inter|Roboto:wght@400
GFONTS_RE = re.compile(r"family=([^&\"'>\s]+)", re.IGNORECASE)

# CSS functions and other non-font tokens (e.g. var(--fontFamily))
_INVALID_FONT_PATTERN = re.compile(
    r"[(){}/#]|^[\d\-]|^var\b|^calc\b|^env\b|^attr\b",
    re.IGNORECASE,
)


def _clean(name: str) -> str:
    return name.strip().strip('"').strip("'").strip()


def _is_valid_font_name(name: str) -> bool:
    if not name:
        return False
    if _INVALID_FONT_PATTERN.search(name):
        return False
    return True


def _extract_font_stacks(css: str) -> list[list[str]]:
    """
    Extract all font-family stacks from CSS as ordered lists.
    Each stack is [primary, fallback1, fallback2, ...].
    """
    stacks: list[list[str]] = []

    for m in FONT_FAMILY_RE.finditer(css):
        stack = []
        for part in m.group(1).split(","):
            name = _clean(part)
            if _is_valid_font_name(name):
                stack.append(name)
        if stack:
            stacks.append(stack)

    return stacks


def extract_fonts_from_css(css: str) -> tuple[set[str], set[str]]:
    """
    Extract fonts from CSS. Returns (primary_fonts, fallback_fonts).
    Primary = first font in each font-family stack or @font-face declarations.
    Fallback = 2nd+ fonts in stacks.
    """
    primary: set[str] = set()
    fallback: set[str] = set()

    # @font-face declarations are always primary (intentionally loaded)
    for m in FONT_FACE_NAME_RE.finditer(css):
        name = _clean(m.group(1))
        if _is_valid_font_name(name):
            primary.add(name)

    # font-family stacks: first = primary, rest = fallback
    for stack in _extract_font_stacks(css):
        primary.add(stack[0])
        for fb in stack[1:]:
            fallback.add(fb)

    # A font declared in @font-face or as primary in any stack is primary
    fallback -= primary

    return primary, fallback


def extract_google_fonts(html: str) -> list[str]:
    """Parse Google Fonts URL families from <link> tags."""
    fonts: set[str] = set()
    for m in GFONTS_RE.finditer(html):
        for family in m.group(1).split("|"):
            name = _clean(family.split(":")[0].replace("+", " "))
            if _is_valid_font_name(name):
                fonts.add(name)
    return sorted(fonts)


def dedupe(lst: list) -> list:
    seen: set = set()
    return [x for x in lst if not (x in seen or seen.add(x))]


# ─── Per-page extraction ───────────────────────────────────────────────────────

def extract_page_data(url: str, base_url: str) -> dict:
    html = fetch(url)
    if html is None:
        return {"url": url, "error": "Failed to fetch", "fonts": [], "primary_fonts": [], "fallback_fonts": [], "css_files": []}

    soup = BeautifulSoup(html, "html.parser")
    primary_fonts: set[str] = set()
    fallback_fonts: set[str] = set()
    css_files: list[str] = []

    # 1. Google Fonts families from <link> hrefs (always primary — explicitly loaded)
    for name in extract_google_fonts(html):
        primary_fonts.add(name)

    # 2. External CSS files
    for link_tag in soup.find_all("link", rel=lambda v: v and "stylesheet" in v):
        href = link_tag.get("href", "")
        if not href:
            continue
        abs_href = urljoin(base_url, href)
        css_files.append(abs_href)

        css_text = fetch(abs_href)
        if css_text:
            pri, fb = extract_fonts_from_css(css_text)
            primary_fonts.update(pri)
            fallback_fonts.update(fb)

    # 3. Inline <style> blocks
    for style_tag in soup.find_all("style"):
        css_text = style_tag.get_text()
        pri, fb = extract_fonts_from_css(css_text)
        primary_fonts.update(pri)
        fallback_fonts.update(fb)

    # 4. style= attributes on elements
    inline_style_re = re.compile(r"font-family\s*:\s*([^;\"']+)", re.IGNORECASE)
    for tag in soup.find_all(style=True):
        style_val = tag.get("style", "")
        for m in inline_style_re.finditer(style_val):
            parts = [_clean(p) for p in m.group(1).split(",") if _is_valid_font_name(_clean(p))]
            if parts:
                primary_fonts.add(parts[0])
                for fb in parts[1:]:
                    fallback_fonts.add(fb)

    # If a font is primary anywhere, it's not a fallback
    fallback_fonts -= primary_fonts

    # "fonts" includes all for backward compatibility
    all_fonts = sorted(primary_fonts | fallback_fonts)

    return {
        "url": url,
        "fonts": all_fonts,
        "primary_fonts": sorted(primary_fonts),
        "fallback_fonts": sorted(fallback_fonts),
        "css_files": css_files,
    }


# ─── Link collector ────────────────────────────────────────────────────────────

def collect_internal_links(html: str, base_url: str, limit: int = 20) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    base_origin = urlparse(base_url).scheme + "://" + urlparse(base_url).netloc

    seen: set[str] = set()
    links: list[str] = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        abs_href = urljoin(base_url, href)
        parsed = urlparse(abs_href)

        if (
            abs_href.startswith(base_origin)
            and not parsed.fragment
            and parsed.scheme in ("http", "https")
            and abs_href not in seen
            and abs_href != base_url
        ):
            seen.add(abs_href)
            links.append(abs_href)
            if len(links) >= limit:
                break

    return links


# ─── Priority page picker ──────────────────────────────────────────────────────

PRIORITY_SLUGS = ["pricing", "docs", "documentation", "about", "contact", "blog", "features"]


def pick_priority_pages(all_links: list[str], top_n: int = 4) -> list[str]:
    priority, others = [], []
    for link in all_links:
        path = urlparse(link).path.lower().strip("/")
        if any(slug in path for slug in PRIORITY_SLUGS):
            priority.append(link)
        else:
            others.append(link)
    return dedupe(priority + others)[:top_n]


# ─── Main scanner ──────────────────────────────────────────────────────────────

async def scan_website(url: str) -> dict:
    """
    Full scan entry point. Runs synchronous HTTP requests in a thread pool
    to keep the async API compatible with the rest of the FastAPI app.

    Returns:
    {
      "base_url": "https://example.com",
      "pages": [
        { "url": "...", "fonts": [...], "primary_fonts": [...], "fallback_fonts": [...], "css_files": [...] },
        ...
      ]
    }
    """
    if not url.startswith("http"):
        url = "https://" + url

    loop = asyncio.get_event_loop()

    def _run_scan():
        print(f"[scanner] Fetching homepage: {url}")
        html = fetch(url)
        if html is None:
            return {"base_url": url, "pages": [{"url": url, "error": "Failed to fetch", "fonts": [], "primary_fonts": [], "fallback_fonts": []}]}

        # Collect internal links from homepage HTML
        all_links = collect_internal_links(html, url)
        print(f"[scanner] Found {len(all_links)} internal links")

        priority_pages = pick_priority_pages(all_links, top_n=4)
        pages_to_visit = [url] + priority_pages
        print(f"[scanner] Will visit {len(pages_to_visit)} pages")

        results = []
        for i, page_url in enumerate(pages_to_visit):
            print(f"[scanner] Scanning ({i+1}/{len(pages_to_visit)}): {page_url}")
            data = extract_page_data(page_url, url)
            path = urlparse(page_url).path or "/"
            results.append({
                "url": page_url,
                "path": path,
                "fonts": data.get("fonts", []),
                "primary_fonts": data.get("primary_fonts", []),
                "fallback_fonts": data.get("fallback_fonts", []),
                "css_files": data.get("css_files", []),
                **({"error": data["error"]} if "error" in data else {}),
            })

        return {"base_url": url, "pages": results}

    # Run blocking I/O in thread pool so we don't block the event loop
    result = await loop.run_in_executor(None, _run_scan)
    return result


# ─── CLI usage ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import json

    target = sys.argv[1] if len(sys.argv) > 1 else "https://stripe.com"
    result = asyncio.run(scan_website(target))

    print("\n" + "=" * 60)
    print(json.dumps(result, indent=2))
