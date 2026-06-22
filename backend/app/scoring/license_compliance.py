"""
scoring/license_compliance.py — License Compliance metric.

Every font detected on the scanned website is looked up directly in the
Monotype Sales Inventory catalog (font_catalog.json, built from
Sales_Inventory_Report_4.23.26.xlsx, first sheet).

Three outcomes per font:

  licensed      – Source is MT Owned / UFDA / 3rd Party Font / Free Fonts
                  → full credit (1.0)

  in_the_wild   – Source is "In The Wild"
                  → partial credit (IN_THE_WILD_CREDIT = 0.6)
                  → customer must check with legal before commercial use

  unknown       – PostScript / family name not found in the catalog at all
                  → no credit (0.0), flagged as license status unknown

Score = (Σ credit per font / total fonts) × 100
"""

from __future__ import annotations

from .font_catalog import classify, IN_THE_WILD

_GENERIC_FALLBACKS = frozenset({"serif", "sans-serif", "monospace", "cursive", "fantasy"})

# Partial credit for "In The Wild" fonts — meaningful but clearly lower than
# fully licensed, signalling that legal review is required.
IN_THE_WILD_CREDIT: float = 0.6


def compute(scan: dict, user_fonts: set | None = None) -> tuple[float, list[str]]:
    """
    Returns (score: float 0–100, violations: list[str]).

    The ``user_fonts`` parameter is accepted for API compatibility but is
    intentionally ignored — classification is done solely via the catalog.
    """
    pages = scan.get("pages", [])

    all_fonts: set[str] = set()
    for p in pages:
        all_fonts.update(f.lower() for f in p.get("fonts", []))

    # Drop pure CSS generic keywords — they carry no license meaning
    candidate_fonts = all_fonts - _GENERIC_FALLBACKS

    if not candidate_fonts:
        return 50.0, ["No fonts detected on scanned pages"]

    licensed: list[str] = []
    in_the_wild: list[str] = []
    unknown: list[str] = []

    for font in candidate_fonts:
        cls = classify(font)
        if cls == "licensed":
            licensed.append(font)
        elif cls == "in_the_wild":
            in_the_wild.append(font)
        else:
            unknown.append(font)

    total = len(candidate_fonts)
    weighted_ok = len(licensed) * 1.0 + len(in_the_wild) * IN_THE_WILD_CREDIT
    score = round((weighted_ok / total) * 100, 1)

    violations: list[str] = []

    for f in in_the_wild:
        violations.append(
            f"Font '{f}' is classified as '{IN_THE_WILD}' in the Monotype catalog — "
            "please consult your legal team before commercial use"
        )

    for f in unknown:
        violations.append(
            f"Font '{f}' was not found in the Monotype catalog — license status unknown"
        )

    return max(score, 10.0), violations
