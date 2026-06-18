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
