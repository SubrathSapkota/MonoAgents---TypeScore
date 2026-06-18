"""
scoring/accessibility_score.py — Accessibility metric.

Converts the accessibility violation report (produced by app.analyzer.accessibility)
into a 0-100 score. More severe violations carry heavier penalties.

Penalty weights:
  critical  → 15 pts per instance
  serious   →  8 pts per instance
  moderate  →  3 pts per instance
  minor     →  1 pt  per instance
"""

from __future__ import annotations


_PENALTY = {
    "critical": 15,
    "serious": 8,
    "moderate": 3,
    "minor": 1,
}

# Show at most this many violation messages in the breakdown
_MAX_SHOWN = 10


def compute(a11y: dict | None) -> tuple[float, list[str]]:
    """
    Returns (score: float, violations: list[str]).

    Parameters
    ----------
    a11y : dict returned by app.analyzer.accessibility.analyze_accessibility(), or None
    """
    if not a11y or "total_violations" not in a11y:
        return 50.0, ["Accessibility data unavailable — could not reach the page"]

    penalty = sum(
        a11y.get(level, 0) * pts
        for level, pts in _PENALTY.items()
    )

    score = max(0.0, 100.0 - penalty)

    violations: list[str] = [
        f"[{v['impact']}] {v['description']} ({v['count']} instance{'s' if v['count'] != 1 else ''})"
        for v in a11y.get("violations", [])[:_MAX_SHOWN]
    ]

    return round(score, 1), violations
