"""
scoring/brand_consistency.py — Brand Consistency metric.

Measures how consistently the same custom fonts appear across all scanned pages.
100 = every page uses the exact same set of custom/branded fonts.
"""

from __future__ import annotations

from .constants import SYSTEM_FONTS


def compute(scan: dict) -> tuple[float, list[str]]:
    """
    Returns (score: float, violations: list[str]).

    Algorithm:
    - For each page, build the set of custom (non-system) fonts.
    - For each unique custom font, measure the fraction of pages that use it.
    - Average those fractions → consistency ratio → score out of 100.
    """
    pages = scan.get("pages", [])
    if not pages:
        return 0.0, ["No pages scanned"]

    page_font_sets: list[set[str]] = []
    for p in pages:
        custom = {f.lower() for f in p.get("fonts", []) if f.lower() not in SYSTEM_FONTS}
        page_font_sets.append(custom)

    if not any(page_font_sets):
        return 50.0, ["No custom fonts detected on any page"]

    all_fonts = set().union(*page_font_sets)
    if not all_fonts:
        return 50.0, ["Only system/generic fonts found"]

    consistency_scores: list[float] = []
    for font in all_fonts:
        pages_with = sum(1 for s in page_font_sets if font in s)
        consistency_scores.append(pages_with / len(pages))

    avg = sum(consistency_scores) / len(consistency_scores) * 100

    violations: list[str] = []
    for font in all_fonts:
        missing_on = [
            pages[i].get("path", "/")
            for i, s in enumerate(page_font_sets)
            if font not in s
        ]
        if missing_on:
            present_on = [
                pages[i].get("path", "/")
                for i, s in enumerate(page_font_sets)
                if font in s
            ]
            violations.append(
                f"Font '{font}' found on {present_on} but missing on {missing_on}"
            )

    return round(avg, 1), violations
