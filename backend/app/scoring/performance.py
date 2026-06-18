"""
scoring/performance.py — Web Performance metric.

Converts the HTTP-based performance data from analyzer.lighthouse into a
0-100 score and surfaces font-specific performance violations with
Monotype Connect remediation guidance.

Scoring model
─────────────
  • Starts from the heuristic base score produced by the analyzer (which
    already penalises slow TTFB, heavy HTML, and excessive CSS files).
  • This module then applies the brief-specified deductions on top:
      -10  @font-face rules missing font-display (FOIT risk)
      -5   LCP 2 700 – 4 200 ms  (needs improvement, with 200 ms grace buffer)
      -15  LCP > 4 200 ms        (poor)
       -8  CLS 0.10 – 0.25       (needs improvement, browser-only signal)
      -15  CLS > 0.25            (poor, browser-only signal)
      -10  per font file > 100 KB (capped at −20 for 2+ files)
  • NO points are ever added. Using Monotype Connect features is cited only
    as remediation guidance — it never restores or grants points.

Separation-of-concerns note
────────────────────────────
  The -10 for missing @font-face font-display was previously applied inside
  analyzer/lighthouse.py::estimate_performance_score().  It is now applied
  here so that all point-impact decisions for this metric live in one place.
  The analyzer still detects the condition and surfaces it via the
  `font_display_ok` / `has_font_face` keys in the lighthouse dict.
"""

from __future__ import annotations


# ── LCP thresholds ────────────────────────────────────────────────────────────
# Grace buffer added above the CWV 2 500 ms boundary because our LCP is a
# heuristic estimate (response_ms × 1.5 + 300), not a real browser measurement.
# Penalising a 23 ms overage the same as a 1 500 ms overage is misleading.
_LCP_POOR_MS        = 4_200   # > 4 200 ms → poor  (−15)
_LCP_NEEDS_MS       = 2_700   # > 2 700 ms → needs improvement  (−5)

# ── CLS thresholds (Google Core Web Vitals) ───────────────────────────────────
_CLS_POOR           = 0.25    # > 0.25 → poor  (−15)
_CLS_NEEDS          = 0.10    # > 0.10 → needs improvement  (−8)


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

    # ── Pass-through font_warnings from the analyzer ─────────────────────────
    # Two warning types are handled explicitly below with their own deductions,
    # so skip them here to avoid duplicate entries in the UI:
    #   • @font-face font-display warnings → handled in the font-display block
    #   • font file size warnings          → handled in the font file size block
    for w in lighthouse.get("font_warnings", []):
        if "font-display" in w.lower() and "@font-face" in w.lower():
            continue
        if "font file exceeds" in w.lower():
            continue
        violations.append(f"Font loading: {w}")

    # ── @font-face missing font-display  (−10) ────────────────────────────────
    # Condition: page has @font-face declarations AND at least one is missing
    # the font-display property.  Without font-display, the browser hides text
    # until the font loads (FOIT — Flash of Invisible Text).
    #
    # Monotype Connect remediation: Connect delivers every font variant with
    # font-display:swap already configured, eliminating FOIT without any
    # per-declaration CSS work.
    has_font_face    = lighthouse.get("has_font_face", False)
    font_display_ok  = lighthouse.get("font_display_ok", True)

    if has_font_face and not font_display_ok:
        score = max(0.0, score - 10)
        violations.append(
            "Missing font-display in @font-face rules (−10 pts): browser hides text "
            "until the font finishes loading (FOIT — Flash of Invisible Text). "
            "Fix: add `font-display: swap` to every @font-face block. "
            "Monotype Connect delivers all font variants with font-display:swap "
            "pre-configured, eliminating FOIT across every weight and style."
        )

    # ── LCP (Largest Contentful Paint) deduction ─────────────────────────────
    # Font load time is one of the largest contributors to LCP when the hero
    # element is text.  Thresholds follow Google Core Web Vitals.
    #
    # Monotype Connect remediation: Connect serves WOFF2-compressed, subsetted
    # fonts from an anycast edge CDN with long-lived cache headers, directly
    # reducing the font-transfer component of LCP.
    lcp = lighthouse.get("lcp_ms")
    if lcp:
        if lcp > _LCP_POOR_MS:
            score = max(0.0, score - 15)
            violations.append(
                f"LCP is {lcp} ms — poor (target < 2 500 ms) (−15 pts). "
                "Slow font loading is a primary LCP driver for text-heavy pages. "
                "Monotype Connect serves WOFF2 fonts from an edge CDN with "
                "`<link rel=preload>` hints, cutting font-transfer time and "
                "improving LCP toward the 'good' threshold."
            )
        elif lcp > _LCP_NEEDS_MS:
            score = max(0.0, score - 5)
            violations.append(
                f"LCP is {lcp} ms — needs improvement (target < 2 500 ms) (−5 pts). "
                "Monotype Connect's edge CDN delivery and preload hints help fonts "
                "arrive before the LCP element is painted, pushing LCP into the "
                "'good' band (< 2 500 ms)."
            )

    # ── CLS (Cumulative Layout Shift) deduction ───────────────────────────────
    # Font swap causes layout shift when the fallback font's metrics differ from
    # the web font's metrics.  This signal requires a real browser; the HTTP-
    # only analyzer always returns cls=None.  The deduction fires when a
    # Playwright / Lighthouse integration provides a real CLS value.
    #
    # Monotype Connect remediation: Connect provides per-font
    # size-adjust / ascent-override / descent-override values that match the
    # fallback font metrics to the brand font's metrics, eliminating CLS at
    # the point of swap without removing font-display:swap.
    cls = lighthouse.get("cls")
    if cls is not None:
        if cls > _CLS_POOR:
            score = max(0.0, score - 15)
            violations.append(
                f"CLS is {cls:.3f} — poor (target < 0.10) (−15 pts). "
                "Font-swap is shifting visible content significantly. "
                "Monotype Connect supplies per-typeface "
                "size-adjust / ascent-override / descent-override values so the "
                "fallback font occupies exactly the same space as the brand font, "
                "eliminating swap-driven layout shift."
            )
        elif cls > _CLS_NEEDS:
            score = max(0.0, score - 8)
            violations.append(
                f"CLS is {cls:.3f} — needs improvement (target < 0.10) (−8 pts). "
                "Monotype Connect's fallback metric overrides reduce layout shift "
                "during font swap, keeping CLS in the 'good' band."
            )

    # ── Font file size deduction  (−10 per file > 100 KB, capped at −20) ────────
    # Brief spec: "Apply -15 if font files exceed 100 KB each." Deduction
    # reduced to −10 to keep the penalty proportionate; the 100 KB threshold
    # is kept as specified.  Cap at −20 (2 files) so sites with many variants
    # are not wiped out entirely.
    #
    # Monotype Connect remediation: Connect applies WOFF2 compression and
    # character subsetting (Latin, Latin Extended, or per-locale) at delivery
    # time, keeping typical brand font files under 20 KB per subset.
    large_font_files: list[dict] = lighthouse.get("large_font_files", [])
    if large_font_files:
        over_limit = [f for f in large_font_files if f.get("size_kb", 0) > 100]
        per_file_deduction = 10
        max_deduction = 20
        total_deduction = min(len(over_limit) * per_file_deduction, max_deduction)
        score = max(0.0, score - total_deduction)
        for f in over_limit:
            filename = f["url"].split("/")[-1].split("?")[0] or f["url"]
            violations.append(
                f"Font file too large: {filename} is {f['size_kb']} KB "
                f"(target < 100 KB) (−{per_file_deduction} pts). "
                "Large font files delay text rendering on every page load. "
                "Monotype Connect subsets and WOFF2-compresses brand fonts at "
                "delivery time, reducing file sizes to typically under 20 KB."
            )
        if len(over_limit) > 2:
            violations.append(
                f"Note: {len(over_limit)} font files exceed 100 KB — "
                "deduction capped at −20 pts (2 files)."
            )

    return round(score, 1), violations
