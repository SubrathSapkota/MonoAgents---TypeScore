"""
scoring/performance.py — Performance metric.

Converts the Lighthouse / HTTP-based performance data into a 0-100 score
and surfaces font-specific performance violations (font-display, LCP, CLS).
"""

from __future__ import annotations


def compute(lighthouse: dict | None) -> tuple[float, list[str]]:
    """
    Returns (score: float, violations: list[str]).

    Parameters
    ----------
    lighthouse : dict returned by app.analyzer.lighthouse.analyze_url(), or None
    """
    if not lighthouse or lighthouse.get("performance") is None:
        return 50.0, ["Performance data unavailable — could not reach the page"]

    score = float(lighthouse["performance"])
    violations: list[str] = []

    for w in lighthouse.get("font_warnings", []):
        violations.append(f"Font loading: {w}")

    lcp = lighthouse.get("lcp_ms")
    if lcp and lcp > 2500:
        violations.append(f"Estimated LCP is {lcp}ms (target < 2500ms)")

    cls = lighthouse.get("cls")
    if cls and cls > 0.1:
        violations.append(f"CLS is {cls} (target < 0.1)")

    return score, violations
