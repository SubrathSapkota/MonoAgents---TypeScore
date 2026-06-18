"""
scoring/developer_experience.py — Developer Experience metric.

Evaluates font-loading best practices from the scanned site's CSS structure:
  - Are fonts loaded via external stylesheets?   (good)
  - Are there excessive inline <style> blocks?   (bad)
  - Is font-display used in @font-face rules?    (required by lighthouse check)
  - Too many CSS files per page?                 (render-blocking risk)
"""

from __future__ import annotations


def compute(scan: dict, lighthouse: dict | None) -> tuple[float, list[str]]:
    """
    Returns (score: float, violations: list[str]).

    Parameters
    ----------
    scan       : raw scan dict from scanner.scan_website()
    lighthouse : dict from lighthouse.analyze_url(), or None
    """
    pages = scan.get("pages", [])
    violations: list[str] = []
    score = 100.0

    total_css = sum(len(p.get("css_files", [])) for p in pages)
    total_inline = sum(len(p.get("inline_styles", [])) for p in pages)

    # No external CSS at all
    if total_css == 0:
        score -= 30
        violations.append("No external CSS files detected — fonts may not be loaded correctly")

    # Excessive inline styles (threshold: 5 per page)
    inline_threshold = len(pages) * 5
    if total_inline > inline_threshold:
        penalty = min(25, (total_inline - inline_threshold) * 2)
        score -= penalty
        violations.append(
            f"Excessive inline styles ({total_inline} blocks across {len(pages)} page(s)) "
            "— hurts maintainability and caching"
        )

    # Too many CSS files → render-blocking risk
    avg_css = total_css / max(len(pages), 1)
    if avg_css > 15:
        score -= 15
        violations.append(
            f"High CSS file count (~{round(avg_css)} per page) — "
            "consider bundling to reduce render-blocking requests"
        )
    elif avg_css > 8:
        score -= 8
        violations.append(
            f"Moderate CSS file count (~{round(avg_css)} per page) — "
            "consider consolidating stylesheets"
        )

    # font-display missing (from lighthouse / HTTP analyzer)
    if lighthouse:
        for w in lighthouse.get("font_warnings", []):
            if "font-display" in w.lower():
                score -= 15
                violations.append(
                    "Missing font-display property in @font-face — "
                    "text is invisible during font load (FOIT)"
                )
                break

    return max(round(score, 1), 0.0), violations
