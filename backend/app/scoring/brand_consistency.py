"""
scoring/brand_consistency.py — Brand Consistency metric (v4).

Unified scoring architecture — NOT mutually exclusive modes.
Fingerprints enrich typography metrics; governance always runs.

Architecture
────────────
Brand Consistency
│
├── Typography Structure (60%)
│   ├── Family Count         — fewer families = tighter brand
│   ├── Role Separation      — heading vs body font discipline
│   ├── Weight Diversity     — constrained weight palette
│   └── Size Scale           — deliberate type scale vs. one-offs
│
├── Governance (25%)
│   ├── Source Governance    — font provider fragmentation (Monotype-critical)
│   ├── Primary Font Dominance — is the brand typeface dominant?
│   └── Rogue Font Detection — unauthorized system fonts creeping in
│
└── Stability (15%)
    ├── Cross-page Stability — same font mix across pages
    └── Fallback Consistency — same fallback stack everywhere

When fingerprints are available:
  Typography Structure + Stability use rich browser-derived metrics.
  Governance ALWAYS runs from HTTP scan data on top.

When fingerprints are NOT available:
  Typography Structure degrades to HTTP-based family counting.
  Stability uses Jaccard similarity across page font sets.
  Governance still runs fully.
"""

from __future__ import annotations

import math
import re

from .constants import (
    SYSTEM_FONTS,
    ALL_STRIPPABLE_SUFFIXES,
    CODE_FONT_MARKERS,
    ICON_FONT_MARKERS,
    CJK_FONT_MARKERS,
    ARABIC_FONT_MARKERS,
    INDIC_FONT_MARKERS,
    ROGUE_SYSTEM_FONTS,
)


# ══════════════════════════════════════════════════════════════════════════════
# FONT FAMILY NORMALIZATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

_CAMEL_SPLIT_RE = re.compile(r"(?<=[a-z\d])(?=[A-Z])")
_ABBREV_BOUNDARY_RE = re.compile(r"(?<=[A-Z]{2})(?=[A-Z][a-z])")
_NUMERIC_SUFFIX_RE = re.compile(r"\d{2,}$")
_MULTI_SPACE_RE = re.compile(r"\s+")

_KNOWN_ABBREVIATIONS = {"CJK"}


def normalize_font_family(raw_name: str) -> str:
    """
    Collapse font variant names into their root family.

    Examples:
        "HelveticaNowMTDisplayBold"      → "helvetica now"
        "HelveticaNowMTDisplayExtraBold" → "helvetica now"
        "Inter-Bold"                     → "inter"
        "NotoSansCJKsc-Regular"          → "noto sans cjk"
    """
    name = raw_name.strip()
    if not name:
        return ""

    name = name.replace("-", " ").replace("_", " ")

    for abbr in _KNOWN_ABBREVIATIONS:
        if abbr in name:
            name = name.replace(abbr, f" {abbr.lower()} ")

    name = _CAMEL_SPLIT_RE.sub(" ", name)
    name = _ABBREV_BOUNDARY_RE.sub(" ", name)
    name = name.lower().strip()

    tokens = name.split()
    while tokens and tokens[-1] in ALL_STRIPPABLE_SUFFIXES:
        tokens.pop()
    if tokens and _NUMERIC_SUFFIX_RE.match(tokens[-1]):
        tokens.pop()

    normalized = " ".join(tokens)
    normalized = _MULTI_SPACE_RE.sub(" ", normalized).strip()
    return normalized or raw_name.lower().strip()


# ══════════════════════════════════════════════════════════════════════════════
# FONT ROLE CLASSIFIER
# ══════════════════════════════════════════════════════════════════════════════

class FontRole:
    BRAND = "brand"
    CODE = "code"
    ICON = "icon"
    CJK = "cjk"
    ARABIC = "arabic"
    INDIC = "indic"
    SYSTEM = "system"


_NORMALIZED_SYSTEM_VARIANTS = {
    "times new", "courier new", "comic sans", "lucida sans",
    "lucida console", "trebuchet", "segoe",
}


def classify_font_role(normalized_name: str, raw_name: str = "") -> str:
    """
    Classify a normalized font name into a role.

    Parameters
    ----------
    normalized_name : the result of normalize_font_family()
    raw_name        : optional original name before normalization, used to detect
                      script-specific fonts whose locale suffixes got stripped
                      (e.g., "NotoSansJP" → normalized "noto sans" but raw reveals JP)
    """
    lower = normalized_name.lower()

    if lower in SYSTEM_FONTS or lower in ROGUE_SYSTEM_FONTS:
        return FontRole.SYSTEM
    if lower in _NORMALIZED_SYSTEM_VARIANTS:
        return FontRole.SYSTEM

    # Check raw name for locale/script indicators that normalization stripped
    raw_lower = raw_name.lower().replace("-", " ").replace("_", " ") if raw_name else ""
    combined = f"{lower} {raw_lower}"

    for marker in CODE_FONT_MARKERS:
        if marker in combined:
            return FontRole.CODE
    for marker in ICON_FONT_MARKERS:
        if marker in combined:
            return FontRole.ICON
    for marker in CJK_FONT_MARKERS:
        if marker in combined:
            return FontRole.CJK
    for marker in ARABIC_FONT_MARKERS:
        if marker in combined:
            return FontRole.ARABIC
    for marker in INDIC_FONT_MARKERS:
        if marker in combined:
            return FontRole.INDIC

    # Detect CJK/script fonts by locale suffix in raw name
    # Apply CamelCase split to raw name to catch "NotoSansJP" → "noto sans jp"
    if raw_lower:
        raw_split = _CAMEL_SPLIT_RE.sub(" ", raw_name).lower() if raw_name else raw_lower
        raw_split = raw_split.replace("-", " ").replace("_", " ")
        _CJK_LOCALE_CODES = {"jp", "kr", "sc", "tc", "hk", "cn", "tw"}
        _ARABIC_LOCALE_CODES = {"ar", "he", "ur", "fa"}
        _INDIC_LOCALE_CODES = {
            "th", "ne", "hi", "bn", "ta", "te", "kn", "ml",
            "gu", "pa", "si", "my", "km", "lo",
        }
        for token in raw_split.split():
            if token in _CJK_LOCALE_CODES:
                return FontRole.CJK
            if token in _ARABIC_LOCALE_CODES:
                return FontRole.ARABIC
            if token in _INDIC_LOCALE_CODES:
                return FontRole.INDIC

    return FontRole.BRAND


# ══════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def _clamp(n: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, n))


def _merge_counts(target: dict, source: dict) -> dict:
    for key, val in (source or {}).items():
        target[key] = target.get(key, 0) + val
    return target


def _grade(score100: float) -> str:
    if score100 >= 90:
        return "A"
    if score100 >= 80:
        return "B"
    if score100 >= 70:
        return "C"
    if score100 >= 60:
        return "D"
    return "F"


# ══════════════════════════════════════════════════════════════════════════════
# PILLAR 1: TYPOGRAPHY STRUCTURE (60%)
# Uses fingerprints when available, degrades to HTTP font list otherwise
# ══════════════════════════════════════════════════════════════════════════════

def _aggregate_fingerprints(pages: list[dict]) -> dict:
    """Combine page fingerprints into a single site-level fingerprint."""
    site = {
        "pages": len(pages),
        "elementsAnalyzed": 0,
        "primaryFamilies": {},
        "weights": {},
        "sizes": {},
        "roleFamilies": {"heading": {}, "body": {}},
        "fallbackStacks": {},
        "inlineOverrides": 0,
        "importantFontRules": 0,
    }

    for p in pages:
        site["elementsAnalyzed"] += p.get("elementsAnalyzed", 0)
        _merge_counts(site["primaryFamilies"], p.get("primaryFamilies"))
        _merge_counts(site["weights"], p.get("weights"))
        _merge_counts(site["sizes"], p.get("sizes"))
        _merge_counts(site["roleFamilies"]["heading"], (p.get("roleFamilies") or {}).get("heading"))
        _merge_counts(site["roleFamilies"]["body"], (p.get("roleFamilies") or {}).get("body"))
        site["inlineOverrides"] += p.get("inlineOverrides", 0)
        site["importantFontRules"] += p.get("importantFontRules", 0)

        for fam, stacks in (p.get("fallbackStacks") or {}).items():
            if fam not in site["fallbackStacks"]:
                site["fallbackStacks"][fam] = set()
            for s in (stacks if isinstance(stacks, list) else [stacks]):
                site["fallbackStacks"][fam].add(s)

    for fam in site["fallbackStacks"]:
        site["fallbackStacks"][fam] = list(site["fallbackStacks"][fam])

    return site


def _family_count_score(site: dict) -> tuple[float, dict]:
    """Fewer distinct primary families = tighter brand. 1-7 is healthy."""
    n = len(site["primaryFamilies"])
    score = 1.0 if n <= 7 else _clamp(1.0 - (n - 7) * 0.12)
    return score, {"distinctFamilies": n, "families": sorted(site["primaryFamilies"].keys())[:8]}


def _role_separation_score(site: dict) -> tuple[float, dict]:
    """Within each role (heading, body), one family should dominate."""
    role_dominance = {}
    scores = []

    for role in ["heading", "body"]:
        counts = list((site["roleFamilies"].get(role) or {}).values())
        total = sum(counts)
        if total == 0:
            continue
        dominance = max(counts) / total
        role_dominance[role] = round(dominance, 3)
        scores.append(dominance)

    score = sum(scores) / len(scores) if scores else 1.0
    return score, {"roleDominance": role_dominance}


def _weight_diversity_score(site: dict) -> tuple[float, dict]:
    """A real type system uses ≤ 4 weights."""
    n = len(site["weights"])
    score = 1.0 if n <= 4 else _clamp(1.0 - (n - 4) * 0.15)
    return score, {"distinctWeights": n, "weights": sorted(site["weights"].keys())}


def _size_scale_score(site: dict) -> tuple[float, dict]:
    """Sizes should sit on a deliberate scale, not scatter as one-offs."""
    sizes = sorted(
        [int(s) for s in site["sizes"].keys() if s.isdigit() and int(s) > 0]
    )
    unique = len(sizes)

    count_score = 1.0 if unique <= 8 else _clamp(1.0 - (unique - 8) * 0.05)

    coherence = 1.0
    if len(sizes) >= 3:
        ratios = [sizes[i] / sizes[i - 1] for i in range(1, len(sizes)) if sizes[i - 1] > 0]
        if ratios:
            mean = sum(ratios) / len(ratios)
            variance = sum((r - mean) ** 2 for r in ratios) / len(ratios)
            cv = math.sqrt(variance) / mean if mean else 0
            coherence = _clamp(1.0 - cv)

    score = count_score * 0.6 + coherence * 0.4
    return score, {"distinctSizes": unique, "countScore": round(count_score, 3), "scaleCoherence": round(coherence, 3)}


def _score_typography_structure_fingerprint(site: dict) -> tuple[float, list[str]]:
    """Typography Structure from fingerprints — 4 sub-metrics, each 0-1."""
    metrics = {
        "familyCount": _family_count_score(site),
        "roleSeparation": _role_separation_score(site),
        "weightDiversity": _weight_diversity_score(site),
        "sizeScale": _size_scale_score(site),
    }

    # Internal weights within Typography Structure pillar
    weights = {"familyCount": 0.30, "roleSeparation": 0.35, "weightDiversity": 0.20, "sizeScale": 0.15}

    weighted = sum(metrics[k][0] * weights[k] for k in weights)
    violations: list[str] = []

    fc_score, fc_detail = metrics["familyCount"]
    if fc_score < 0.8:
        violations.append(
            f"Font family sprawl: {fc_detail['distinctFamilies']} distinct families detected "
            f"(target ≤ 7). Families: {fc_detail['families'][:6]}. "
            "A focused brand uses 1-3 typefaces with script-specific additions as needed."
        )

    rs_score, rs_detail = metrics["roleSeparation"]
    if rs_score < 0.75:
        violations.append(
            f"Weak role separation: heading/body roles lack a dominant family. "
            f"Role dominance: {rs_detail['roleDominance']}. "
            "Strong brands assign one family to headings and one to body text."
        )

    wd_score, wd_detail = metrics["weightDiversity"]
    if wd_score < 0.8:
        violations.append(
            f"Weight sprawl: {wd_detail['distinctWeights']} font weights in use "
            f"(target ≤ 4). Weights: {wd_detail['weights']}."
        )

    ss_score, ss_detail = metrics["sizeScale"]
    if ss_score < 0.7:
        violations.append(
            f"Size scale drift: {ss_detail['distinctSizes']} distinct sizes "
            f"(coherence: {ss_detail['scaleCoherence']:.0%}). "
            "Sizes should follow a deliberate modular scale."
        )

    return weighted, violations


def _score_typography_structure_http(page_font_data: list[dict], all_brand_fonts: set[str]) -> tuple[float, list[str]]:
    """Typography Structure from HTTP data — simplified family count check."""
    n = len(all_brand_fonts)
    score = 1.0 if n <= 7 else _clamp(1.0 - (n - 7) * 0.12)
    violations: list[str] = []

    if n > 10:
        violations.append(
            f"Font family sprawl: {n} distinct brand families detected (target ≤ 7). "
            "A focused brand uses 1-3 core typefaces with script-specific additions as needed."
        )
    elif n > 7:
        violations.append(
            f"Moderate font variety: {n} brand families detected (target ≤ 7)."
        )

    return score, violations


# ══════════════════════════════════════════════════════════════════════════════
# PILLAR 2: GOVERNANCE (25%) — ALWAYS RUNS from HTTP scan data
# Source Governance, Primary Font Dominance, Rogue Font Detection
# ══════════════════════════════════════════════════════════════════════════════

_FONT_PROVIDERS = {
    "monotype": {
        "patterns": ["fast.fonts.net", "fonts.monotype.com", "monotype.com"],
        "label": "Monotype Fonts",
        "risk": "low",
    },
    "google": {
        "patterns": ["fonts.googleapis.com", "fonts.gstatic.com"],
        "label": "Google Fonts",
        "risk": "medium",
    },
    "adobe": {
        "patterns": ["use.typekit.net", "p.typekit.net"],
        "label": "Adobe Fonts",
        "risk": "medium",
    },
    "cdn": {
        "patterns": ["cdn.", "cdnjs.", "unpkg.", "jsdelivr."],
        "label": "Public CDN",
        "risk": "high",
    },
}


def _detect_font_sources(pages: list[dict]) -> dict[str, set[str]]:
    """Detect font providers from CSS URLs across all pages."""
    detected: dict[str, set[str]] = {}

    for p in pages:
        for css_url in p.get("css_files", []):
            lower_url = css_url.lower()

            matched = False
            for provider_id, provider in _FONT_PROVIDERS.items():
                if any(pattern in lower_url for pattern in provider["patterns"]):
                    if provider["label"] not in detected:
                        detected[provider["label"]] = set()
                    detected[provider["label"]].add(css_url)
                    matched = True
                    break

            if not matched and (lower_url.endswith(".css") or ".css?" in lower_url):
                if "Self-hosted" not in detected:
                    detected["Self-hosted"] = set()
                detected["Self-hosted"].add(css_url)

    return detected


def _score_source_governance(pages: list[dict]) -> tuple[float, list[str]]:
    """
    Source Governance — how fragmented is font delivery?
    Single provider = excellent. Multiple = governance risk.
    Scored 0.0-1.0.
    """
    detected = _detect_font_sources(pages)
    source_count = len(detected) if detected else 1
    violations: list[str] = []

    if source_count <= 1:
        score = 1.0
        provider_name = list(detected.keys())[0] if detected else "Self-hosted"
        violations.append(f"✓ Font delivery centralized: {provider_name}")
    elif source_count == 2:
        score = 0.55
        providers = sorted(detected.keys())
        violations.append(
            f"Source Governance: Font providers detected:\n"
            + "".join(f"  • {p}\n" for p in providers)
            + f"Risk: Typography assets distributed across {source_count} providers, "
            "making license tracking difficult.\n"
            "Recommendation: Centralize font delivery through Monotype Connect."
        )
    else:
        score = max(0.2, 0.55 - (source_count - 2) * 0.15)
        providers = sorted(detected.keys())
        violations.append(
            f"Source Governance: Font providers detected:\n"
            + "".join(f"  • {p}\n" for p in providers)
            + f"Risk: Typography assets distributed across {source_count} providers, "
            "making license tracking and governance difficult.\n"
            "Recommendation: Centralize font delivery through Monotype Connect."
        )

    return score, violations


def _score_primary_font_dominance(
    page_font_data: list[dict],
    all_brand_fonts: set[str],
    total_pages: int,
) -> tuple[float, list[str], str]:
    """
    Primary Font Dominance — is the brand typeface present everywhere?
    Returns (score 0-1, violations, primary_font_name).
    """
    violations: list[str] = []

    if not all_brand_fonts:
        return 0.0, ["No brand fonts detected — site relies on system fonts."], ""

    brand_page_counts: dict[str, int] = {}
    for font in all_brand_fonts:
        brand_page_counts[font] = sum(1 for pd in page_font_data if font in pd["brand"])

    primary_font = max(brand_page_counts, key=brand_page_counts.get)
    primary_coverage = brand_page_counts[primary_font] / total_pages

    score = min(1.0, primary_coverage / 0.70)

    if primary_coverage < 0.50:
        violations.append(
            f"Low primary font dominance: '{primary_font}' covers only "
            f"{primary_coverage:.0%} of pages. "
            "Monotype Connect ensures consistent delivery via a global embed snippet."
        )
    elif primary_coverage < 0.70:
        violations.append(
            f"Moderate primary font dominance: '{primary_font}' covers "
            f"{primary_coverage:.0%} of pages (target ≥ 70%)."
        )

    return score, violations, primary_font


def _score_rogue_font_detection(
    pages: list[dict],
    page_font_data: list[dict],
) -> tuple[float, list[str]]:
    """
    Rogue Font Detection — pages with only system fonts and no brand presence.
    These represent unauthorized/accidental system font usage.
    """
    violations: list[str] = []
    rogue_pages = []

    for i, pd in enumerate(page_font_data):
        has_intentional = pd["brand"] or pd["code"] or pd["icon"] or pd["script"]
        if not has_intentional and pd["system"]:
            rogue_pages.append(pages[i].get("url", pages[i].get("path", f"page_{i}")))

    rogue_count = len(rogue_pages)
    total = len(pages)

    if rogue_count == 0:
        score = 1.0
    elif rogue_count == 1:
        score = 0.7
    elif rogue_count == 2:
        score = 0.4
    else:
        score = max(0.0, 0.3 - (rogue_count - 3) * 0.1)

    if rogue_pages:
        violations.append(
            f"Rogue typography on {rogue_count}/{total} page(s): "
            f"{rogue_pages[:4]}. "
            "These pages have no brand font — only unauthorized system defaults."
        )

    return score, violations


def _score_governance(
    pages: list[dict],
    page_font_data: list[dict],
    all_brand_fonts: set[str],
) -> tuple[float, list[str], str]:
    """
    Governance pillar — combines Source Governance, Primary Font Dominance,
    and Rogue Font Detection.

    Internal weights: Source Governance 40%, Dominance 35%, Rogue 25%.
    Returns (score 0-1, violations, primary_font_name).
    """
    total_pages = len(pages)
    all_violations: list[str] = []

    src_score, src_viols = _score_source_governance(pages)
    all_violations.extend(src_viols)

    dom_score, dom_viols, primary_font = _score_primary_font_dominance(
        page_font_data, all_brand_fonts, total_pages
    )
    all_violations.extend(dom_viols)

    rogue_score, rogue_viols = _score_rogue_font_detection(pages, page_font_data)
    all_violations.extend(rogue_viols)

    # Internal weights within Governance pillar
    weighted = src_score * 0.40 + dom_score * 0.35 + rogue_score * 0.25

    return weighted, all_violations, primary_font


# ══════════════════════════════════════════════════════════════════════════════
# PILLAR 3: STABILITY (15%)
# Cross-page Stability + Fallback Consistency
# ══════════════════════════════════════════════════════════════════════════════

def _cross_page_stability_fingerprint(pages: list[dict]) -> tuple[float, dict] | None:
    """Cosine similarity of each page's family vector to the site centroid."""
    if len(pages) < 2:
        return None

    families: set[str] = set()
    for p in pages:
        families.update((p.get("primaryFamilies") or {}).keys())
    dims = sorted(families)

    if not dims:
        return None

    vectors = []
    for p in pages:
        v = [p.get("primaryFamilies", {}).get(f, 0) for f in dims]
        norm = math.hypot(*v) or 1.0
        vectors.append([x / norm for x in v])

    centroid = [sum(vec[i] for vec in vectors) / len(vectors) for i in range(len(dims))]
    c_norm = math.hypot(*centroid) or 1.0
    c_unit = [x / c_norm for x in centroid]

    sims = [sum(v[i] * c_unit[i] for i in range(len(dims))) for v in vectors]
    score = _clamp(sum(sims) / len(sims))
    return score, {"pages": len(pages)}


def _fallback_consistency_score(site: dict) -> tuple[float, dict]:
    """Each primary family should ship the same fallback stack everywhere."""
    families = site["fallbackStacks"]
    if not families:
        return 1.0, {"families": {}}

    per_family = {}
    total = 0.0
    for fam, stacks in families.items():
        distinct = len(stacks)
        per_family[fam] = distinct
        total += 1.0 / distinct

    score = total / len(families)
    return score, {"distinctStacksPerFamily": per_family}


def _cross_page_stability_http(page_font_data: list[dict]) -> float:
    """Jaccard similarity of brand font sets across page pairs."""
    brand_sets = [pd["brand"] for pd in page_font_data]
    total_pages = len(brand_sets)

    if total_pages <= 1:
        return 1.0

    jaccard_sum = 0.0
    pair_count = 0
    for i in range(total_pages):
        for j in range(i + 1, total_pages):
            a, b = brand_sets[i], brand_sets[j]
            if not a and not b:
                jaccard = 1.0
            elif not a or not b:
                jaccard = 0.0
            else:
                jaccard = len(a & b) / len(a | b)
            jaccard_sum += jaccard
            pair_count += 1

    return jaccard_sum / pair_count if pair_count else 1.0


def _score_stability_fingerprint(fingerprints: list[dict], site: dict) -> tuple[float, list[str]]:
    """Stability from fingerprints — Cross-page + Fallback Consistency."""
    violations: list[str] = []

    # Cross-page stability (weight 60% of stability pillar)
    cross = _cross_page_stability_fingerprint(fingerprints)
    cross_score = cross[0] if cross else 1.0

    if cross and cross[0] < 0.8:
        violations.append(
            "Cross-page instability: pages use noticeably different font mixes. "
            "A stable typography system presents the same fonts regardless of template. "
            "Monotype Connect's global embed ensures identical availability across all pages."
        )

    # Fallback consistency (weight 40% of stability pillar)
    fb_score, fb_detail = _fallback_consistency_score(site)

    if fb_score < 0.8:
        inconsistent = [f for f, n in fb_detail["distinctStacksPerFamily"].items() if n > 1]
        if inconsistent:
            violations.append(
                f"Inconsistent fallback stacks for: {inconsistent[:5]}. "
                "Each family should ship the same fallback declaration site-wide."
            )

    weighted = cross_score * 0.60 + fb_score * 0.40
    return weighted, violations


def _score_stability_http(page_font_data: list[dict]) -> tuple[float, list[str]]:
    """Stability from HTTP data — Jaccard similarity of brand font sets."""
    violations: list[str] = []
    avg_jaccard = _cross_page_stability_http(page_font_data)

    if avg_jaccard < 0.50:
        violations.append(
            f"Low cross-page stability ({avg_jaccard:.0%} similarity). "
            "Pages use significantly different font sets."
        )
    elif avg_jaccard < 0.75:
        violations.append(
            f"Moderate cross-page stability ({avg_jaccard:.0%} similarity)."
        )

    return avg_jaccard, violations


# ══════════════════════════════════════════════════════════════════════════════
# SCAN DATA NORMALIZATION (shared between pillars)
# ══════════════════════════════════════════════════════════════════════════════

def _normalize_scan_pages(
    pages: list[dict],
    font_script_map: dict[str, str] | None = None,
) -> tuple[list[dict], set[str], set[str]]:
    """
    Normalize and classify all fonts per page.

    Uses the scanner's primary/fallback distinction: only fonts that appear as
    the FIRST font in a font-family stack (the intentional choice) are considered
    brand fonts. Fonts that only appear in fallback positions are treated as system.

    Parameters
    ----------
    pages           : list of page dicts from scanner
    font_script_map : optional {family_lower: "cjk"|"indic"|"arabic"} from lighthouse
                      unicode-range detection (preferred over name-based heuristics)

    Returns (page_font_data, all_normalized, all_brand_fonts).
    """
    script_map = font_script_map or {}
    page_font_data: list[dict[str, set[str]]] = []
    all_normalized: set[str] = set()
    all_brand_fonts: set[str] = set()

    for p in pages:
        # Use primary_fonts if available (new scanner), fall back to all fonts
        primary_set = set(f.lower().strip() for f in p.get("primary_fonts", []))
        fallback_set = set(f.lower().strip() for f in p.get("fallback_fonts", []))
        has_position_data = bool(primary_set or fallback_set)

        raw_fonts = p.get("fonts", [])
        page_families: dict[str, set[str]] = {
            "brand": set(), "code": set(), "icon": set(),
            "script": set(), "system": set(),
        }

        for raw in raw_fonts:
            raw_lower = raw.lower().strip()
            if raw_lower in SYSTEM_FONTS:
                page_families["system"].add(raw_lower)
                continue

            normalized = normalize_font_family(raw)
            if not normalized or normalized in SYSTEM_FONTS:
                page_families["system"].add(normalized or raw_lower)
                continue

            # If this font ONLY appears in fallback positions, treat as system
            if has_position_data and raw_lower not in primary_set:
                page_families["system"].add(normalized)
                continue

            # Priority 1: Use unicode-range-based script detection from lighthouse
            if raw_lower in script_map:
                page_families["script"].add(normalized)
                all_normalized.add(normalized)
                continue
            if normalized in script_map:
                page_families["script"].add(normalized)
                all_normalized.add(normalized)
                continue

            # Priority 2: Name-based classification (script keywords + locale codes)
            role = classify_font_role(normalized, raw)
            all_normalized.add(normalized)

            if role == FontRole.BRAND:
                page_families["brand"].add(normalized)
                all_brand_fonts.add(normalized)
            elif role == FontRole.CODE:
                page_families["code"].add(normalized)
            elif role == FontRole.ICON:
                page_families["icon"].add(normalized)
            elif role in (FontRole.CJK, FontRole.ARABIC, FontRole.INDIC):
                page_families["script"].add(normalized)
            else:
                page_families["system"].add(normalized)

        page_font_data.append(page_families)

    return page_font_data, all_normalized, all_brand_fonts


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API — UNIFIED SCORING
# ══════════════════════════════════════════════════════════════════════════════

# Pillar weights
_PILLAR_WEIGHTS = {
    "typography_structure": 0.60,
    "governance": 0.25,
    "stability": 0.15,
}


def compute(
    scan: dict,
    approved_fonts: set | None = None,
    lighthouse: dict | None = None,
) -> tuple[float, list[str]]:
    """
    Returns (score: float 0-100, violations: list[str]).

    Unified architecture — all three pillars always contribute:
      • Typography Structure (60%) — fingerprints if available, else HTTP
      • Governance (25%) — ALWAYS from HTTP scan data
      • Stability (15%) — fingerprints if available, else Jaccard

    Parameters
    ----------
    scan           : dict from scanner.scan_website(), optionally enriched with
                     "fingerprints" from app.extractor.extract_site()
    approved_fonts : optional set of lowercase font names the user has approved
                     as their brand palette (from user font library)
    lighthouse     : optional dict from lighthouse analyzer — contains
                     "font_script_map" for unicode-range-based script classification
    """
    pages = scan.get("pages", [])
    if not pages:
        return 0.0, ["No pages scanned — unable to assess brand consistency"]

    fingerprints = scan.get("fingerprints")
    has_fingerprints = (
        fingerprints and isinstance(fingerprints, list) and len(fingerprints) > 0
    )

    # Extract unicode-range-based script map from lighthouse (if available)
    font_script_map = (lighthouse or {}).get("font_script_map")

    # Normalize HTTP scan data (always needed for Governance)
    page_font_data, all_normalized, all_brand_fonts = _normalize_scan_pages(
        pages, font_script_map=font_script_map
    )

    if not all_normalized:
        return 15.0, [
            "No custom/brand fonts detected on any page — the site relies entirely "
            "on system fonts with no typographic brand identity. "
            "Monotype Connect provides a centrally-managed brand font library."
        ]

    all_violations: list[str] = []

    # ── PILLAR 1: Typography Structure (60%) ─────────────────────────────────
    if has_fingerprints:
        site = _aggregate_fingerprints(fingerprints)
        typo_score, typo_viols = _score_typography_structure_fingerprint(site)
    else:
        site = None
        typo_score, typo_viols = _score_typography_structure_http(
            page_font_data, all_brand_fonts
        )
    all_violations.extend(typo_viols)

    # ── PILLAR 2: Governance (25%) — ALWAYS runs ─────────────────────────────
    gov_score, gov_viols, primary_font = _score_governance(
        pages, page_font_data, all_brand_fonts
    )
    all_violations.extend(gov_viols)

    # ── PILLAR 3: Stability (15%) ────────────────────────────────────────────
    if has_fingerprints and site:
        stab_score, stab_viols = _score_stability_fingerprint(fingerprints, site)
    else:
        stab_score, stab_viols = _score_stability_http(page_font_data)
    all_violations.extend(stab_viols)

    # ── COMBINE PILLARS ──────────────────────────────────────────────────────
    total_score = (
        typo_score * _PILLAR_WEIGHTS["typography_structure"]
        + gov_score * _PILLAR_WEIGHTS["governance"]
        + stab_score * _PILLAR_WEIGHTS["stability"]
    ) * 100.0

    # ── APPROVED FONT CHECK (optional overlay) ───────────────────────────────
    if approved_fonts and len(approved_fonts) > 0:
        total_score, all_violations = _apply_approved_font_check(
            page_font_data, all_brand_fonts, total_score, all_violations, approved_fonts
        )

    # ── INFORMATIONAL SUMMARY ────────────────────────────────────────────────
    brand_count = len(all_brand_fonts)
    code_count = len({f for pd in page_font_data for f in pd["code"]})
    script_count = len({f for pd in page_font_data for f in pd["script"]})
    extras = []
    if code_count:
        extras.append(f"{code_count} code")
    if script_count:
        extras.append(f"{script_count} script/locale")
    inventory = f"{brand_count} brand {'family' if brand_count == 1 else 'families'}"
    if extras:
        inventory += f", {', '.join(extras)}"

    data_source = "browser fingerprints" if has_fingerprints else "HTTP scan"
    all_violations.append(
        f"Typography inventory (normalized): {inventory}. "
        f"Data source: {data_source}."
    )

    final_score = max(0.0, min(100.0, round(total_score, 1)))
    grade = _grade(final_score)

    if final_score >= 85:
        all_violations.insert(0, f"Strong brand consistency (Grade {grade}) — typography is well-governed.")
    elif final_score >= 70:
        all_violations.insert(0, f"Good brand consistency (Grade {grade}).")

    return final_score, all_violations


def _apply_approved_font_check(
    page_font_data: list[dict],
    all_brand_fonts: set[str],
    base_score: float,
    base_violations: list[str],
    approved_fonts: set[str],
) -> tuple[float, list[str]]:
    """
    When the user has configured an approved font palette, penalize any
    detected font that falls outside that list.

    Formula from executive summary: Score -= 10 per extra font.
    Capped so this adjustment alone can't reduce more than 40 pts.
    """
    approved_normalized = {normalize_font_family(f) for f in approved_fonts}
    unapproved = all_brand_fonts - approved_normalized

    if not unapproved or not approved_normalized:
        return base_score, base_violations

    penalty = min(len(unapproved) * 10, 40)
    adjusted_score = max(0.0, base_score - penalty)

    violation_msg = (
        f"{len(unapproved)} font(s) outside the approved brand palette "
        f"(−{penalty} pts): {sorted(unapproved)[:6]}. "
        f"Approved: {sorted(approved_normalized)[:4]}. "
        "Unapproved fonts fragment brand identity. Remove them or add to "
        "your approved list in Monotype Connect."
    )
    base_violations.append(violation_msg)

    return round(adjusted_score, 1), base_violations
