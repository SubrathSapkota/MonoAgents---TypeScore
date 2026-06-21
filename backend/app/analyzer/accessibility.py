"""
accessibility.py — Font-focused accessibility checker.

Uses requests + BeautifulSoup to detect typography and font-related accessibility
violations from static HTML/CSS.  Only checks directly caused by font or text-rendering
decisions are included.

Checks performed:
  1. html[lang] missing        — browser cannot select the correct font/script for the page
  2. CSS font sizes below 12px — type is too small for low-vision users
  3. CSS near-white text colour — likely contrast failure tied to the font/colour pairing
  4. Ultra-thin font weights    — font-weight 100/200 lacks stroke contrast for body text
  5. Untagged PDFs              — embedded fonts without structure tags block screen readers
  6. Lang/font script mismatch  — declared script (Arabic, CJK, etc.) with only Latin fonts
  7. Viewport blocks text scaling — users with low vision cannot zoom to a readable size
"""

from __future__ import annotations

import asyncio
import io
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.utils.http_client import fetch, fetch_bytes

# ── pypdf availability (optional dependency — PDF check gracefully skipped if absent) ──
try:
    import pypdf as _pypdf
    _PYPDF_AVAILABLE = True
except ImportError:
    _pypdf = None  # type: ignore[assignment]
    _PYPDF_AVAILABLE = False


# ── Pre-compiled patterns ──────────────────────────────────────────────────────

# "color:" but NOT "background-color:" — light/near-white values only.
# 6-digit hex: each byte e0–ff (#f0f0f0, #eeeeee, #ffffff …)
# 3-digit hex:  each nibble e–f  (#eee, #fff …)
# rgb/rgba:     all three channels ≥ 224 — avoids false-positives on saturated colours.
_LIGHT_COLOR_RE = re.compile(
    r"(?<![a-z-])color\s*:"
    r"\s*(?:"
    r"#(?:[e-f][0-9a-f]){3}"
    r"|#[e-f]{3}"
    r"|rgba?\(\s*(2[2-9]\d|[3-9]\d{2})\s*,\s*(2[2-9]\d|[3-9]\d{2})\s*,"
    r"\s*(2[2-9]\d|[3-9]\d{2})"
    r")",
    re.IGNORECASE,
)

# "font-size: Npx" declarations.
_FONT_SIZE_PX_RE = re.compile(
    r"font-size\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*px",
    re.IGNORECASE,
)

# font-weight: 100 or 200 (ultra-thin).
_THIN_WEIGHT_RE = re.compile(
    r"font-weight\s*:\s*(100|200)\b",
    re.IGNORECASE,
)

# Viewport content that blocks user text scaling.
# Precise boundary prevents "maximum-scale=10" from matching "maximum-scale=1".
_VIEWPORT_NO_ZOOM_RE = re.compile(
    r"user-scalable\s*=\s*no"
    r"|maximum-scale\s*=\s*1(?:\.0+)?(?:\s*[,;]|$)",
    re.IGNORECASE,
)

# href ending in .pdf (with optional query string).
_PDF_HREF_RE = re.compile(r"\.pdf(\?[^\s\"']*)?$", re.IGNORECASE)

# Font-size threshold (px).
_MIN_ACCESSIBLE_FONT_PX = 12.0

# Maximum PDFs to download per scan.  Kept low to stay within the 60s total scan budget.
_MAX_PDF_SCANS = 2

# Per-PDF download timeout (seconds).  Tight enough to not blow the overall scan budget
# even in the worst case: 2 PDFs × 8s = 16s maximum added latency.
_PDF_FETCH_TIMEOUT_S = 8

# Maximum PDF size to download.  2 MB is enough to read the document catalog header.
_PDF_MAX_BYTES = 2 * 1024 * 1024

# Language codes → script name for non-Latin languages.
# Presence in this dict means the page's declared script cannot be rendered by
# a typical Latin-only web font — a system-font fallback is then likely.
_NON_LATIN_LANG_SCRIPTS: dict[str, str] = {
    # Arabic script
    "ar": "Arabic", "fa": "Arabic", "ur": "Arabic", "ps": "Arabic",
    # Hebrew script
    "he": "Hebrew", "yi": "Hebrew",
    # CJK
    "zh": "CJK", "ja": "CJK", "ko": "Korean",
    # Indic
    "hi": "Devanagari", "mr": "Devanagari", "ne": "Devanagari",
    "bn": "Bengali", "as": "Bengali",
    "ta": "Tamil", "te": "Telugu", "kn": "Kannada", "ml": "Malayalam",
    "pa": "Gurmukhi", "gu": "Gujarati",
    # Southeast Asian
    "th": "Thai", "lo": "Lao", "my": "Burmese", "km": "Khmer",
    # Other
    "ka": "Georgian", "am": "Ethiopic", "ti": "Ethiopic", "si": "Sinhala",
}

# Font name substrings (lowercase) that indicate multilingual/non-Latin coverage.
_MULTILINGUAL_FONT_KEYWORDS: frozenset[str] = frozenset({
    # General
    "noto", "source han", "unicode",
    # Arabic
    "arabic", "amiri", "scheherazade", "lateef", "reem kufi",
    "cairo", "tajawal", "almarai", "readex",
    # Hebrew
    "hebrew", "david", "frank ruehl", "alef", "heebo",
    # CJK
    "cjk", "ming", "gothic", "hiragino", "meiryo", "nanum",
    "malgun", "simhei", "simsun", "yu gothic",
    # Devanagari / Indic
    "devanagari", "kohinoor", "mukta", "mangal", "hind", "lohit",
    # Thai
    "thai", "sarabun", "prompt", "kanit",
    # Other scripts
    "georgian", "ethiopic",
})


# ── CSS helpers ────────────────────────────────────────────────────────────────

def check_color_contrast_hints(css_text: str) -> list[str]:
    """Flag near-white text colours likely to fail contrast against light backgrounds."""
    if _LIGHT_COLOR_RE.search(css_text):
        return [
            "Possible low-contrast text colours detected in CSS "
            "(near-white text applied where background may also be light)"
        ]
    return []


def check_small_font_hints(css_text: str) -> list[str]:
    """Flag font-size declarations below the minimum accessible size."""
    small: list[float] = [
        float(m.group(1))
        for m in _FONT_SIZE_PX_RE.finditer(css_text)
        if float(m.group(1)) < _MIN_ACCESSIBLE_FONT_PX
    ]
    if not small:
        return []
    min_size = min(small)
    count = len(small)
    return [
        f"Font size {min_size}px found in CSS "
        f"({count} declaration{'s' if count != 1 else ''} below {_MIN_ACCESSIBLE_FONT_PX}px) "
        f"— small type reduces readability for users with low vision"
    ]


def check_thin_font_weight(css_text: str) -> list[str]:
    """
    Flag ultra-thin font-weight declarations (100 or 200).  These weights have
    insufficient stroke contrast for body text legibility, especially at small sizes
    or on non-ideal display environments.
    """
    matches = _THIN_WEIGHT_RE.findall(css_text)
    if not matches:
        return []
    weights = sorted({int(w) for w in matches})
    count = len(matches)
    return [
        f"Ultra-thin font weight(s) {weights} found in CSS "
        f"({count} declaration{'s' if count != 1 else ''}) — "
        f"weights 100–200 lack sufficient stroke contrast for readable body text"
    ]


def check_lang_font_mismatch(lang: str, css_text: str) -> list[str]:
    """
    If the page declares a non-Latin language but CSS contains only Latin font families,
    flag a glyph-coverage gap — the browser will substitute a system font, breaking both
    readability and brand typography for that script.
    """
    lang_code = lang.split("-")[0].lower()   # "zh-CN" → "zh"
    script = _NON_LATIN_LANG_SCRIPTS.get(lang_code)
    if not script:
        return []   # Latin language — no mismatch possible

    # Collect all font-family values mentioned in the CSS
    all_font_text = " ".join(
        re.findall(r"font-family\s*:\s*([^;}\n]+)", css_text, re.IGNORECASE)
    ).lower()

    has_compatible_font = any(kw in all_font_text for kw in _MULTILINGUAL_FONT_KEYWORDS)
    if has_compatible_font:
        return []

    return [
        f'Page declares lang="{lang}" ({script} script) but no {script}-capable '
        f"font family detected in CSS — browser will substitute a system font, "
        f"breaking brand typography for {script}-script content"
    ]


# ── PDF helpers ────────────────────────────────────────────────────────────────

def _is_pdf_tagged(pdf_bytes: bytes) -> bool:
    """
    Return True if the PDF has accessibility structure tags (MarkInfo.Marked = True).
    An untagged PDF means screen readers cannot extract text or navigate headings.
    Returns False if pypdf is unavailable or the file cannot be parsed.
    """
    if not _PYPDF_AVAILABLE:
        return False
    try:
        reader = _pypdf.PdfReader(io.BytesIO(pdf_bytes))
        root_ref = reader.trailer.get("/Root")
        if root_ref is None:
            return False
        root = root_ref.get_object() if hasattr(root_ref, "get_object") else root_ref
        mark_info = root.get("/MarkInfo")
        if mark_info is None:
            return False
        mark_obj = mark_info.get_object() if hasattr(mark_info, "get_object") else mark_info
        return bool(mark_obj.get("/Marked", False))
    except Exception as e:
        print(f"[a11y] PDF tag check error: {e}")
        return False


def check_pdf_accessibility(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """
    Collect PDF links from the page, download up to _MAX_PDF_SCANS, and flag any
    that are not tagged for accessibility.

    Intentionally synchronous — called via run_in_executor from the async analyser
    so PDF downloads do not block the FastAPI event loop.
    """
    pdf_urls: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if _PDF_HREF_RE.search(href):
            abs_url = urljoin(base_url, href)
            if abs_url not in seen:
                seen.add(abs_url)
                pdf_urls.append(abs_url)

    if not pdf_urls:
        return []

    to_scan = pdf_urls[:_MAX_PDF_SCANS]
    print(
        f"[a11y] Found {len(pdf_urls)} PDF link(s), scanning {len(to_scan)} "
        f"(timeout {_PDF_FETCH_TIMEOUT_S}s each, max {_PDF_MAX_BYTES // 1024 // 1024}MB each)"
    )

    scanned = 0
    untagged = 0
    for pdf_url in to_scan:
        data = fetch_bytes(pdf_url, timeout=_PDF_FETCH_TIMEOUT_S, max_bytes=_PDF_MAX_BYTES)
        if data is None:
            continue
        scanned += 1
        if not _is_pdf_tagged(data):
            untagged += 1

    if scanned == 0 or untagged == 0:
        return []

    return [{
        "id": "pdf-untagged",
        "impact": "critical",
        "count": untagged,
        "description": (
            f"{untagged} of {scanned} scanned PDF(s) missing accessibility tags — "
            f"screen readers cannot extract text or navigate document structure; "
            f"embedded fonts likely lack ToUnicode tables required for text selection"
        ),
    }]


# ── Main analyser ─────────────────────────────────────────────────────────────

async def analyze_accessibility(url: str) -> dict:
    """
    Font-focused accessibility analysis.

    Returns::

        {
            "total_violations": int,
            "critical": int,
            "serious": int,
            "moderate": int,
            "minor": int,
            "violations": [
                {
                    "id": str,
                    "impact": "critical" | "serious" | "moderate" | "minor",
                    "count": int,
                    "description": str,
                },
                ...
            ],
        }

    On fetch failure the "error" key is also present and all counts are 0.
    The scorer treats the "error" key as an unavailable-data signal (score=50).
    """
    if not url.startswith("http"):
        url = "https://" + url

    print(f"[a11y] Fetching {url} …")
    html = fetch(url)
    if html is None:
        return {
            "error": "Failed to fetch page",
            "total_violations": 0,
            "critical": 0,
            "serious": 0,
            "moderate": 0,
            "minor": 0,
            "violations": [],
        }

    soup = BeautifulSoup(html, "html.parser")
    violations: list[dict] = []

    # ── 1. html[lang] — font/script selection ─────────────────────────────────
    # Without a lang attribute the browser cannot determine which script font to
    # use.  Non-Latin scripts risk system-font fallback that breaks brand typography.
    html_tag = soup.find("html")
    page_lang: str = ""
    if html_tag:
        page_lang = html_tag.get("lang", "")
        if not page_lang:
            violations.append({
                "id": "html-has-lang",
                "impact": "serious",
                "count": 1,
                "description": (
                    "HTML element missing lang attribute — browser cannot select the "
                    "correct font/script variant; non-Latin scripts risk system-font "
                    "fallback that breaks brand typography"
                ),
            })

    # ── 2–5. CSS-based checks ─────────────────────────────────────────────────
    all_css = "\n".join(tag.get_text() for tag in soup.find_all("style"))
    for link_tag in soup.find_all("link", rel=lambda v: v and "stylesheet" in v)[:2]:
        href = link_tag.get("href", "")
        if href:
            css_text = fetch(urljoin(url, href))
            if css_text:
                all_css += "\n" + css_text

    if all_css:
        # 2. Font size below 12px
        for issue in check_small_font_hints(all_css):
            violations.append({
                "id": "font-size",
                "impact": "moderate",
                "count": 1,
                "description": issue,
            })

        # 3. Near-white text colour heuristic
        for issue in check_color_contrast_hints(all_css):
            violations.append({
                "id": "color-contrast",
                "impact": "serious",
                "count": 1,
                "description": issue,
            })

        # 4. Ultra-thin font weights (100 / 200)
        for issue in check_thin_font_weight(all_css):
            violations.append({
                "id": "font-weight-thin",
                "impact": "serious",
                "count": 1,
                "description": issue,
            })

        # 5. Lang declared but no compatible font in CSS
        if page_lang:
            for issue in check_lang_font_mismatch(page_lang, all_css):
                violations.append({
                    "id": "lang-font-mismatch",
                    "impact": "serious",
                    "count": 1,
                    "description": issue,
                })

    # ── 6. PDF accessibility ──────────────────────────────────────────────────
    # Run in a thread executor so the blocking PDF downloads do not stall the
    # FastAPI event loop while waiting for each file to transfer.
    loop = asyncio.get_event_loop()
    pdf_violations = await loop.run_in_executor(
        None, check_pdf_accessibility, soup, url
    )
    for v in pdf_violations:
        violations.append(v)

    # ── 7. Viewport meta — blocks text scaling ────────────────────────────────
    # When user scaling is disabled, visitors with low vision cannot zoom to a
    # readable font size (WCAG 1.4.4 Resize Text, Level AA).
    viewport_meta = soup.find("meta", attrs={"name": "viewport"})
    if viewport_meta:
        content = viewport_meta.get("content", "")
        if _VIEWPORT_NO_ZOOM_RE.search(content):
            violations.append({
                "id": "meta-viewport",
                "impact": "critical",
                "count": 1,
                "description": (
                    "Viewport meta tag prevents text scaling — users with low vision "
                    "cannot zoom to a readable font size (WCAG 1.4.4 Resize Text)"
                ),
            })

    # ── Sort and aggregate ────────────────────────────────────────────────────
    _SEVERITY_ORDER = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}
    violations.sort(key=lambda x: (_SEVERITY_ORDER.get(x["impact"], 4), -x["count"]))

    severity_counts: dict[str, int] = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
    for v in violations:
        severity_counts[v["impact"]] = severity_counts.get(v["impact"], 0) + v["count"]

    total = sum(severity_counts.values())
    print(
        f"[a11y] Done — {total} issues found "
        f"(critical={severity_counts['critical']}, serious={severity_counts['serious']})"
    )

    return {
        "total_violations": total,
        **severity_counts,
        "violations": violations,
    }


if __name__ == "__main__":
    import asyncio
    import json
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "https://stripe.com"
    result = asyncio.run(analyze_accessibility(target))
    print(json.dumps(result, indent=2))
