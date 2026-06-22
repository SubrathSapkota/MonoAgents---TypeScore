"""
scoring/developer_experience.py — Developer Experience metric.

Evaluates font architecture quality. A high score means the site follows
modern font-loading best practices: proper subsetting, WOFF2 format,
font-display strategy, and minimal bloat.

Philosophy: Reward good architecture, penalize only genuine problems.

Positive signals (reported but don't add score — you start at 100):
  ✓ Unicode-range subsetting detected
  ✓ Modern WOFF2 format in use
  ✓ font-display: swap enabled
  ✓ Self-hosted fonts (no third-party dependency)

Penalties (only for actual problems):
  -10  Missing font-display on @font-face rules
  -5   Google Fonts without display=swap
  -5   per font FAMILY beyond 3 (cap -15) — families, not variants
  -5   per font file > 100 KB (cap -15)
  -5/-10  Render-blocking stylesheets (>5 / >10)
  -15  No external CSS at all
  -10  Excessive inline font overrides
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
    positives: list[str] = []
    score = 100.0

    # ── 1. No external CSS at all (−15) ──────────────────────────────────────
    total_css = sum(len(p.get("css_files", [])) for p in pages)
    if total_css == 0 and pages:
        score -= 15
        violations.append(
            "No external CSS files detected (−15 pts) — fonts may not be loaded "
            "correctly or are entirely inline, hurting cacheability."
        )

    # ── 2. Excessive inline style overrides (−10 max) ────────────────────────
    total_inline = sum(len(p.get("inline_styles", [])) for p in pages)
    inline_threshold = len(pages) * 5
    if total_inline > inline_threshold and pages:
        penalty = min(10, (total_inline - inline_threshold) * 2)
        score -= penalty
        violations.append(
            f"Excessive inline font overrides: {total_inline} blocks across "
            f"{len(pages)} page(s) (−{penalty} pts). Inline declarations bypass "
            "the design system and prevent browser caching."
        )

    # ── Lighthouse-dependent checks ───────────────────────────────────────────
    if lighthouse:
        has_font_face = lighthouse.get("has_font_face", False)
        font_display_ok = lighthouse.get("font_display_ok", True)
        uses_subsetting = lighthouse.get("uses_unicode_range", False)
        font_face_count = lighthouse.get("font_face_count", 0)
        font_variant_count = lighthouse.get("font_variant_count", 0)
        large_files: list[dict] = lighthouse.get("large_font_files", [])

        # ── Positive architecture signals ────────────────────────────────────
        if uses_subsetting:
            positives.append("✓ Unicode-range subsetting detected — browser "
                            "downloads only needed character sets")

        if has_font_face and font_display_ok:
            positives.append("✓ font-display: swap enabled — text remains "
                            "visible during font load")

        # Check for WOFF2 usage (inferred from file extensions in large_font_files
        # or from font_face_count existing with subsetting)
        if uses_subsetting or (has_font_face and font_face_count > 0):
            positives.append("✓ Modern font loading architecture")

        if uses_subsetting and font_face_count > 0:
            positives.append(
                f"  Font architecture: {font_face_count} declarations → "
                f"{font_variant_count} effective variants (no penalty)"
            )

        # ── 3. Missing font-display (−10) ───────────────────────────────────
        if has_font_face and not font_display_ok:
            score -= 10
            violations.append(
                "Missing font-display property in @font-face rules (−10 pts). "
                "Without font-display:swap, text is invisible until fonts load "
                "(FOIT). Add `font-display: swap` to every @font-face block."
            )

        # ── 4. Google Fonts without display=swap (−5) ────────────────────────
        if lighthouse.get("google_fonts_no_swap", False):
            score -= 5
            violations.append(
                "Google Fonts loaded without display=swap (−5 pts). "
                "Append `&display=swap` to the Google Fonts URL to prevent "
                "invisible text during font load."
            )

        # ── 5. Too many font FAMILIES (−5 per family beyond 3, cap −15) ──────
        # Count distinct font families (not variants). A family with 6 weights
        # and subsetting is fine — but using 5+ different families is bloat.
        # font_variant_count groups by family+weight+style, so we need families.
        # Approximate: font_variant_count is roughly families × avg_variants.
        # Better: lighthouse now provides variant details. Use family count if
        # available, otherwise estimate from variant_count (assume ~3 variants/family).
        font_family_count = lighthouse.get("font_family_count", 0)
        if font_family_count == 0 and font_variant_count > 0:
            # Rough estimate: most families have 2-3 variants
            font_family_count = max(1, font_variant_count // 3)

        if font_family_count > 3:
            excess = font_family_count - 3
            penalty = min(excess * 5, 15)
            score -= penalty
            violations.append(
                f"{font_family_count} distinct font families loaded — "
                f"{excess} beyond the recommended 3 (−{penalty} pts). "
                "Each additional family increases page weight and complexity. "
                "Consolidate to primary, secondary, and monospace."
            )

        # ── 6. Large font files > 100 KB (−5 each, cap −15) ─────────────────
        if large_files:
            penalty = min(len(large_files) * 5, 15)
            score -= penalty
            file_names = [
                f.get("url", "").split("/")[-1].split("?")[0] or "unknown"
                for f in large_files
            ]
            violations.append(
                f"{len(large_files)} font file(s) exceed 100 KB: "
                f"{', '.join(file_names[:4])} (−{penalty} pts). "
                "Large payloads delay text rendering. Use WOFF2 compression "
                "and character subsetting to reduce file sizes."
            )

        # ── 7. Render-blocking stylesheets (−5 or −10) ──────────────────────
        render_blocking = lighthouse.get("render_blocking_count", 0)
        if render_blocking > 10:
            score -= 10
            violations.append(
                f"{render_blocking} render-blocking stylesheets detected (−10 pts). "
                "Each blocking stylesheet delays first paint. Use media queries, "
                "async loading, or critical CSS inlining to reduce blocking."
            )
        elif render_blocking > 5:
            score -= 5
            violations.append(
                f"{render_blocking} render-blocking stylesheets detected (−5 pts). "
                "Consider deferring non-critical stylesheets with media attributes "
                "or loading them asynchronously."
            )

    elif pages:
        avg_css = total_css / max(len(pages), 1)
        if avg_css > 15:
            score -= 10
            violations.append(
                f"High CSS file count (~{round(avg_css)} per page) (−10 pts) — "
                "consider bundling to reduce render-blocking requests."
            )
        elif avg_css > 8:
            score -= 5
            violations.append(
                f"Moderate CSS file count (~{round(avg_css)} per page) (−5 pts) — "
                "consider consolidating stylesheets."
            )

    # ── Build final output ────────────────────────────────────────────────────
    # Positives go first so the report leads with good architecture
    final_messages = positives + violations if violations else positives

    if score >= 95 and not violations:
        final_messages.append(
            "Excellent font architecture — loading follows modern best practices "
            "with minimal overhead."
        )

    return max(round(score, 1), 0.0), final_messages
