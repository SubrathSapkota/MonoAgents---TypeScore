"""
accessibility.py — HTTP-based accessibility checker.
Uses requests + BeautifulSoup to check for common accessibility issues
without requiring a browser. Focuses on font/text related a11y concerns.
"""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.utils.http_client import fetch


def check_color_contrast_hints(css_text: str) -> list[str]:
    """
    Heuristic: flag very light text colors (white or near-white) that might
    have contrast issues. Not a full contrast ratio check but catches common mistakes.
    """
    issues = []
    light_color_re = re.compile(
        r"color\s*:\s*(#(?:f{3,6}|e{6}|fff|eee|ddd)|rgba?\(\s*2[5-9]\d|rgba?\(\s*[3-9]\d{2})",
        re.IGNORECASE,
    )
    if light_color_re.search(css_text):
        issues.append("Possible low-contrast text colors detected in CSS")
    return issues


def check_small_font_hints(css_text: str) -> list[str]:
    """Flag font sizes below 12px."""
    issues = []
    size_re = re.compile(r"font-size\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*px", re.IGNORECASE)
    for m in size_re.finditer(css_text):
        size = float(m.group(1))
        if size < 12:
            issues.append(f"Font size {size}px found — may be too small for readability")
            break
    return issues


async def analyze_accessibility(url: str) -> dict:
    """
    HTTP-based accessibility analysis. Checks for common a11y issues
    that can be detected from static HTML/CSS:
    - Missing alt text on images
    - Missing lang attribute on <html>
    - Missing document title
    - Form inputs without labels
    - Small font sizes in CSS
    - Missing aria-label on buttons/links with no text
    """
    if not url.startswith("http"):
        url = "https://" + url

    print(f"[a11y] Fetching {url} …")
    html = fetch(url)
    if html is None:
        return {"error": "Failed to fetch page", "total_violations": 0, "violations": []}

    soup = BeautifulSoup(html, "html.parser")
    violations = []

    # 1. html[lang] missing
    html_tag = soup.find("html")
    if html_tag and not html_tag.get("lang"):
        violations.append({
            "id": "html-has-lang",
            "impact": "serious",
            "count": 1,
            "description": "HTML element missing lang attribute",
        })

    # 2. Missing <title>
    if not soup.find("title") or not soup.find("title").get_text(strip=True):
        violations.append({
            "id": "document-title",
            "impact": "serious",
            "count": 1,
            "description": "Page is missing a <title> element",
        })

    # 3. Images missing alt text
    imgs_no_alt = [
        img for img in soup.find_all("img")
        if not img.get("alt") and not img.get("role") == "presentation"
    ]
    if imgs_no_alt:
        violations.append({
            "id": "image-alt",
            "impact": "critical",
            "count": len(imgs_no_alt),
            "description": f"{len(imgs_no_alt)} image(s) missing alt attribute",
        })

    # 4. Form inputs without labels
    inputs = soup.find_all("input", type=lambda t: t not in ["hidden", "submit", "button", "image", None] or t is None)
    unlabeled = []
    for inp in inputs:
        inp_id = inp.get("id")
        has_label = (
            (inp_id and soup.find("label", attrs={"for": inp_id}))
            or inp.get("aria-label")
            or inp.get("aria-labelledby")
            or inp.get("title")
            or inp.get("placeholder")
        )
        if not has_label:
            unlabeled.append(inp)
    if unlabeled:
        violations.append({
            "id": "label",
            "impact": "critical",
            "count": len(unlabeled),
            "description": f"{len(unlabeled)} form input(s) without accessible labels",
        })

    # 5. Buttons with no accessible text
    buttons_no_text = []
    for btn in soup.find_all("button"):
        text = btn.get_text(strip=True)
        if not text and not btn.get("aria-label") and not btn.get("aria-labelledby") and not btn.get("title"):
            buttons_no_text.append(btn)
    if buttons_no_text:
        violations.append({
            "id": "button-name",
            "impact": "critical",
            "count": len(buttons_no_text),
            "description": f"{len(buttons_no_text)} button(s) have no accessible name",
        })

    # 6. Links with no text
    links_no_text = []
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        img = a.find("img", alt=True)
        if not text and not img and not a.get("aria-label") and not a.get("title"):
            links_no_text.append(a)
    if links_no_text:
        violations.append({
            "id": "link-name",
            "impact": "serious",
            "count": len(links_no_text),
            "description": f"{len(links_no_text)} link(s) have no accessible text",
        })

    # 7. CSS-based checks (inline styles + external CSS)
    all_css = ""
    for style_tag in soup.find_all("style"):
        all_css += style_tag.get_text() + "\n"

    # Fetch up to 2 external CSS files for font-size checks
    css_links = soup.find_all("link", rel=lambda v: v and "stylesheet" in v)[:2]
    for link_tag in css_links:
        href = link_tag.get("href", "")
        if href:
            abs_href = urljoin(url, href)
            css_text = fetch(abs_href)
            if css_text:
                all_css += css_text + "\n"

    if all_css:
        for issue in check_small_font_hints(all_css):
            violations.append({
                "id": "font-size",
                "impact": "moderate",
                "count": 1,
                "description": issue,
            })
        for issue in check_color_contrast_hints(all_css):
            violations.append({
                "id": "color-contrast",
                "impact": "serious",
                "count": 1,
                "description": issue,
            })

    # 8. meta viewport check (prevents zoom)
    viewport_meta = soup.find("meta", attrs={"name": "viewport"})
    if viewport_meta:
        content = viewport_meta.get("content", "")
        if "user-scalable=no" in content or "maximum-scale=1" in content:
            violations.append({
                "id": "meta-viewport",
                "impact": "critical",
                "count": 1,
                "description": "Viewport meta tag prevents user scaling — accessibility violation",
            })

    # Sort by severity
    severity_order = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}
    violations.sort(key=lambda x: (severity_order.get(x["impact"], 4), -x["count"]))

    severity_counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
    for v in violations:
        key = v["impact"]
        severity_counts[key] = severity_counts.get(key, 0) + v["count"]

    total = sum(severity_counts.values())
    print(f"[a11y] Done — {total} issues found (critical={severity_counts['critical']}, "
          f"serious={severity_counts['serious']})")

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
