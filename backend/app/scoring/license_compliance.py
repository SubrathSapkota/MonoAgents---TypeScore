"""
scoring/license_compliance.py — License Compliance metric.

Scores how well fonts used on the website match the user's licensed font library.

Two modes:
  1. User has a font library  → check every custom font against it.
  2. No library provided      → heuristic: penalise heavy use of system fonts.
"""

from __future__ import annotations

from .constants import SYSTEM_FONTS

_GENERIC_FALLBACKS = {"serif", "sans-serif", "monospace", "cursive", "fantasy"}


def compute(scan: dict, user_fonts: set | None = None) -> tuple[float, list[str]]:
    """
    Returns (score: float, violations: list[str]).

    Parameters
    ----------
    scan       : raw scan dict produced by scanner.scan_website()
    user_fonts : optional set of lowercase font names the user has licensed
    """
    pages = scan.get("pages", [])
    all_fonts: set[str] = set()
    for p in pages:
        all_fonts.update(f.lower() for f in p.get("fonts", []))

    custom = all_fonts - SYSTEM_FONTS
    system_used = all_fonts & SYSTEM_FONTS
    real_system = system_used - _GENERIC_FALLBACKS

    violations: list[str] = []

    # ── Mode 1: user has a licensed font library ──────────────────────────────
    if user_fonts is not None:
        if not custom and not real_system:
            return 50.0, ["No fonts detected on scanned pages"]

        unlicensed: list[str] = []
        for font in custom | real_system:
            if font not in _GENERIC_FALLBACKS:
                matched = any(
                    font in lib_font or lib_font in font
                    for lib_font in user_fonts
                )
                if not matched:
                    unlicensed.append(font)

        if not unlicensed:
            return 100.0, []

        total_non_generic = len(custom | real_system)
        penalty_ratio = len(unlicensed) / max(total_non_generic, 1)
        score = round((1 - penalty_ratio) * 100, 1)

        for f in unlicensed:
            violations.append(f"Font '{f}' not found in your licensed library")

        return max(score, 10.0), violations

    # ── Mode 2: no library — heuristic ───────────────────────────────────────
    if not custom:
        violations.append("No custom/licensed web fonts detected — using only system defaults")
        return 30.0, violations

    total = len(custom) + len(real_system)
    if total == 0:
        return 100.0, violations

    ratio = len(custom) / total
    score = round(ratio * 100, 1)

    for f in real_system:
        violations.append(f"System font '{f}' used — may not be brand-approved")

    return max(score, 20.0), violations
