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
    "-apple-system", "blinkmacsystemfont", "segoe ui", "segoe ui adjusted",
    # Normalized forms (after CamelCase split / hyphen removal)
    "blink mac system font", "sans serif", "system ui",
    "ui serif", "ui sans serif", "ui monospace", "ui rounded",
    "apple system", "segoe ui adjusted",
    "liberation sans", "liberation serif", "liberation mono",
    # CSS keywords (not fonts)
    "inherit", "initial", "unset", "revert",
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
    # Script identifiers only — NOT individual font names
    "cjk", "chinese", "japanese", "korean",
    "hangul", "hiragana", "katakana", "kanji",
    # Generic descriptors strongly associated with CJK typographic traditions
    "hei", "song", "ming", "fang",
    "mincho", "myeongjo",
}

ARABIC_FONT_MARKERS: set[str] = {
    # Script identifiers only
    "arabic", "naskh", "kufi", "thuluth", "nastaliq", "ruqah",
    "hebrew", "urdu", "farsi", "persian",
}

INDIC_FONT_MARKERS: set[str] = {
    # Script names — these identify the SCRIPT, not specific font products
    "devanagari", "bengali", "tamil", "telugu", "kannada",
    "gujarati", "gurmukhi", "malayalam", "oriya", "odia",
    "sinhala", "tibetan", "thai", "lao", "khmer", "myanmar",
    "nepali", "hindi", "marathi", "sanskrit",
}

# Unicode range blocks for script detection (from @font-face unicode-range)
# Used by lighthouse.py to classify fonts by their character coverage.
SCRIPT_UNICODE_RANGES: dict[str, list[tuple[int, int]]] = {
    "cjk": [
        (0x4E00, 0x9FFF),    # CJK Unified Ideographs
        (0x3040, 0x309F),    # Hiragana
        (0x30A0, 0x30FF),    # Katakana
        (0xAC00, 0xD7AF),    # Hangul Syllables
        (0x3400, 0x4DBF),    # CJK Extension A
        (0xF900, 0xFAFF),    # CJK Compatibility Ideographs
        (0x2E80, 0x2EFF),    # CJK Radicals Supplement
    ],
    "indic": [
        (0x0900, 0x097F),    # Devanagari
        (0x0980, 0x09FF),    # Bengali
        (0x0A00, 0x0A7F),    # Gurmukhi
        (0x0A80, 0x0AFF),    # Gujarati
        (0x0B00, 0x0B7F),    # Oriya
        (0x0B80, 0x0BFF),    # Tamil
        (0x0C00, 0x0C7F),    # Telugu
        (0x0C80, 0x0CFF),    # Kannada
        (0x0D00, 0x0D7F),    # Malayalam
        (0x0D80, 0x0DFF),    # Sinhala
        (0x0E00, 0x0E7F),    # Thai
        (0x0E80, 0x0EFF),    # Lao
        (0x0F00, 0x0FFF),    # Tibetan
        (0x1000, 0x109F),    # Myanmar
        (0x1780, 0x17FF),    # Khmer
    ],
    "arabic": [
        (0x0600, 0x06FF),    # Arabic
        (0x0750, 0x077F),    # Arabic Supplement
        (0x0590, 0x05FF),    # Hebrew
        (0xFB50, 0xFDFF),    # Arabic Presentation Forms-A
        (0xFE70, 0xFEFF),    # Arabic Presentation Forms-B
    ],
}

# Rogue fonts: system fonts that indicate lack of brand typography
# when used as primary (not fallback) fonts.
ROGUE_SYSTEM_FONTS: set[str] = {
    "arial", "helvetica", "times new roman", "times", "courier new",
    "courier", "verdana", "georgia", "tahoma", "trebuchet ms",
    "impact", "comic sans ms", "palatino", "garamond",
    "lucida console", "lucida sans", "segoe ui",
}
