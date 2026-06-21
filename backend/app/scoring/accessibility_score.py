"""
scoring/accessibility_score.py — Accessibility metric.

Converts the accessibility violation report (produced by app.analyzer.accessibility)
into a 0-100 score. Starts at 100 and deducts only — no additive points.

Penalty weights (per instance, capped per violation type):
  critical  → 15 pts per instance, max 30 pts deducted for any single violation type
  serious   →  8 pts per instance, max 20 pts deducted for any single violation type
  moderate  →  3 pts per instance, max  9 pts deducted for any single violation type
  minor     →  1 pt  per instance, max  3 pts deducted for any single violation type

Per-type caps prevent a single category from collapsing the score to zero while
other violation types go unrepresented.
"""

from __future__ import annotations


_PENALTY: dict[str, int] = {
    "critical": 15,
    "serious": 8,
    "moderate": 3,
    "minor": 1,
}

# Maximum points deducted for any single violation type regardless of instance count.
_TYPE_CAP: dict[str, int] = {
    "critical": 30,
    "serious": 20,
    "moderate": 9,
    "minor": 3,
}

# Show at most this many violation messages in the breakdown.
_MAX_SHOWN = 10

# Monotype Connect remediation guidance, keyed by violation id.
# Only violations where Monotype Connect directly addresses the typography root cause
# receive a hint.  No points are added — guidance appears as informational text only.
_MONOTYPE_CONNECT_HINTS: dict[str, str] = {
    "font-size": (
        "Monotype Connect: select typefaces with high legibility at body sizes — "
        "generous x-height, open apertures, and sufficient stroke contrast — "
        "so text remains readable at smaller sizes without forcing users to zoom."
    ),
    "color-contrast": (
        "Monotype Connect: fonts with high stroke contrast or thin hairlines fail "
        "contrast thresholds at small sizes or on coloured backgrounds; choose "
        "typefaces designed for screen legibility and enforce a minimum weight "
        "standard across your brand palette."
    ),
    "html-has-lang": (
        "Monotype Connect: ensure your licensed font library covers every language "
        "your site serves — gaps in glyph coverage force browsers to substitute "
        "system fonts, breaking both the script rendering and brand typography."
    ),
    "meta-viewport": (
        "Monotype Connect: selecting a highly legible typeface with a strong x-height "
        "and open letterforms reduces user reliance on browser zoom — a well-chosen "
        "brand font remains readable at default sizes, softening the impact of this "
        "violation for the majority of users."
    ),
    "font-weight-thin": (
        "Monotype Connect: enforce a minimum weight floor (300 or above for body copy) "
        "across your brand font tokens — approved weight standards prevent ultra-thin "
        "variants from being applied to body text where stroke contrast is critical."
    ),
    "lang-font-mismatch": (
        "Monotype Connect: your licensed font library should cover every script your "
        "content serves — Monotype's multilingual catalogue provides brand-consistent "
        "rendering across Arabic, CJK, Devanagari, and other non-Latin scripts, "
        "eliminating system-font fallback for international audiences."
    ),
}


def compute(a11y: dict | None) -> tuple[float, list[str]]:
    """
    Returns (score: float, violations: list[str]).

    Parameters
    ----------
    a11y : dict returned by app.analyzer.accessibility.analyze_accessibility(), or None.
           A score of 50.0 is returned when data is unavailable or the page fetch failed.
    """
    # Treat fetch errors as unavailable rather than zero-penalty (score=100).
    # analyze_accessibility() sets "error" when the page cannot be reached; in that
    # case total_violations=0 and severity keys are absent, which would otherwise
    # produce a perfect score of 100 — clearly wrong.
    if not a11y or "total_violations" not in a11y or a11y.get("error"):
        return 50.0, ["Accessibility data unavailable — could not reach the page"]

    violations_list = a11y.get("violations", [])

    # Compute penalty using per-violation-type caps sourced from the violation list
    # rather than aggregate severity counts.  This gives accurate per-type control
    # and is robust if severity-count keys are absent (e.g. on partial fetch).
    penalty = 0.0
    for v in violations_list:
        impact = v.get("impact", "minor")
        count = v.get("count", 1)
        pts_per = _PENALTY.get(impact, 1)
        cap = _TYPE_CAP.get(impact, 2)
        penalty += min(count * pts_per, cap)

    score = max(0.0, 100.0 - penalty)

    violation_msgs: list[str] = []
    for v in violations_list[:_MAX_SHOWN]:
        msg = (
            f"[{v['impact']}] {v['description']} "
            f"({v['count']} instance{'s' if v['count'] != 1 else ''})"
        )
        hint = _MONOTYPE_CONNECT_HINTS.get(v.get("id", ""))
        if hint:
            msg += f" — {hint}"
        violation_msgs.append(msg)

    return round(score, 1), violation_msgs
