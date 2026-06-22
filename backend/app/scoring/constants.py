"""
scoring/constants.py — Shared constants used across scoring modules.
"""

from __future__ import annotations

# Score contribution weights (must sum to 1.0)
WEIGHTS: dict[str, float] = {
    "brand_consistency": 0.20,
    "license_compliance": 0.30,
    "performance": 0.20,
    "accessibility": 0.15,
    "developer_experience": 0.15,
}

# Fonts that are pre-installed on most operating systems.
# Using only system fonts indicates no custom brand typography.
SYSTEM_FONTS: set[str] = {
    "arial", "helvetica", "times new roman", "times", "courier new",
    "courier", "verdana", "georgia", "palatino", "garamond", "comic sans ms",
    "trebuchet ms", "impact", "tahoma", "lucida console", "lucida sans",
    "system-ui", "serif", "sans-serif", "monospace", "cursive", "fantasy",
    "ui-serif", "ui-sans-serif", "ui-monospace", "ui-rounded",
    "-apple-system", "blinkmacsystemfont", "segoe ui",
}

# ── Font normalization constants ──────────────────────────────────────────────
# Used by brand_consistency.py to collapse font variants into root families.

WEIGHT_SUFFIXES: set[str] = {
    "thin", "hairline", "ultralight", "extralight", "light",
    "regular", "normal", "book", "medium", "demibold", "semibold",
    "bold", "extrabold", "ultrabold", "black", "heavy", "extrablack",
    "w1", "w2", "w3", "w4", "w5", "w6", "w7", "w8", "w9",
    # Modifier words that only appear as parts of compound weight names
    "extra", "ultra", "semi", "demi",
}

STYLE_SUFFIXES: set[str] = {
    "italic", "oblique", "roman", "upright", "slanted",
}

WIDTH_SUFFIXES: set[str] = {
    "condensed", "compressed", "narrow", "extended", "expanded", "wide",
    "ultracondensed", "extracondensed", "semicondensed",
    "semiexpanded", "extraexpanded", "ultraexpanded",
}

OPTICAL_SUFFIXES: set[str] = {
    "display", "text", "micro", "caption", "headline", "subhead",
    "banner", "poster", "deck", "small",
}

FORMAT_SUFFIXES: set[str] = {
    "variable", "vf", "var", "static",
}

FOUNDRY_SUFFIXES: set[str] = {
    "mt", "lt", "std", "pro", "offc", "web", "wgl", "neue",
    "itc", "bt", "ef", "ff", "otf", "ttf", "woff",
    "w01", "w02", "w03", "w04", "w05",
}

# Locale/script codes appended to font names (e.g., "NotoSansCJKsc")
LOCALE_SUFFIXES: set[str] = {
    "sc", "tc", "jp", "kr", "hk", "cn", "tw", "th", "ar", "he",
}

# Short weight abbreviations used in PostScript-style font names
WEIGHT_ABBREVIATIONS: set[str] = {
    "bd", "bk", "bl", "cn", "dm", "el", "ex", "hv", "it",
    "lt", "md", "ob", "rg", "sb", "th", "ul", "xb", "xbd",
}

ALL_STRIPPABLE_SUFFIXES: set[str] = (
    WEIGHT_SUFFIXES | STYLE_SUFFIXES | WIDTH_SUFFIXES
    | OPTICAL_SUFFIXES | FORMAT_SUFFIXES | FOUNDRY_SUFFIXES
    | LOCALE_SUFFIXES | WEIGHT_ABBREVIATIONS
)

# ── Font role classification ──────────────────────────────────────────────────

CODE_FONT_MARKERS: set[str] = {
    "mono", "code", "console", "terminal", "fira code", "jet brains",
    "jetbrains", "source code", "cascadia", "inconsolata", "menlo",
    "hack", "iosevka", "droid sans mono", "ubuntu mono", "courier",
    "roboto mono", "sf mono", "ibm plex mono", "noto mono",
    "dm mono", "space mono", "anonymous pro", "liberation mono",
}

ICON_FONT_MARKERS: set[str] = {
    "icon", "awesome", "material", "glyph", "symbol", "icomoon",
    "fontello", "ionicon", "feather", "phosphor", "remix",
    "bootstrap", "boxicon", "line icon", "themify", "typicon",
}

CJK_FONT_MARKERS: set[str] = {
    "hei", "song", "ming", "kai", "fang", "xianghe",
    "noto sans cjk", "noto serif cjk", "noto sans sc", "noto sans tc",
    "noto sans jp", "noto sans kr", "noto serif sc", "noto serif jp",
    "source han", "pingfang", "hiragino", "yu gothic", "yu mincho",
    "microsoft yahei", "meiryo", "malgun", "simsun", "simhei",
    "ms gothic", "ms mincho", "apple sd gothic", "apple myungjo",
    "nanum", "wenquanyi", "droid sans japanese", "droid sans fallback",
    "sarasa", "lxgw", "oppo sans", "dotum", "gulim", "batang", "myeongjo",
}

ARABIC_FONT_MARKERS: set[str] = {
    "naskh", "kufi", "thuluth", "nastaliq", "ruqah", "arabic",
    "noto sans arabic", "noto kufi", "geeza", "al bayan",
    "baghdad", "decotype", "diwan", "farah",
}

INDIC_FONT_MARKERS: set[str] = {
    "devanagari", "bengali", "tamil", "telugu", "kannada",
    "gujarati", "gurmukhi", "malayalam", "oriya", "sinhala",
    "tibetan", "thai", "lao", "khmer", "myanmar", "noto sans",
}

# Rogue fonts: system fonts that indicate lack of brand typography
# when used as primary (not fallback) fonts.
ROGUE_SYSTEM_FONTS: set[str] = {
    "arial", "helvetica", "times new roman", "times", "courier new",
    "courier", "verdana", "georgia", "tahoma", "trebuchet ms",
    "impact", "comic sans ms", "palatino", "garamond",
    "lucida console", "lucida sans", "segoe ui",
}
