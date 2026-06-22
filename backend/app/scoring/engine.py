"""
scoring/engine.py — Composite scoring coordinator.

Final Score = (0.20 × B) + (0.30 × L) + (0.20 × P) + (0.15 × A) + (0.15 × D)

Each metric lives in its own module:
  brand_consistency.py    → B
  license_compliance.py   → L
  performance.py          → P
  accessibility_score.py  → A
  developer_experience.py → D
"""

from __future__ import annotations

from .constants import WEIGHTS
from .brand_consistency import compute as brand_consistency_score
from .license_compliance import compute as license_compliance_score
from .performance import compute as performance_score
from .accessibility_score import compute as accessibility_score
from .developer_experience import compute as developer_experience_score


def compute_scores(
    scan: dict,
    lighthouse: dict | None = None,
    a11y: dict | None = None,
    user_fonts: set | None = None,
) -> dict:
    """
    Master scoring function.

    Parameters
    ----------
    scan        : raw scan result from scanner.scan_website()
    lighthouse  : performance/font metrics from analyzer.lighthouse.analyze_url()
    a11y        : accessibility report from analyzer.accessibility.analyze_accessibility()
    user_fonts  : optional set of lowercase font names the user has licensed

    Returns
    -------
    {
      "overall_score": 74.2,
      "breakdown": {
        "brand_consistency":    {"score": 85, "weight": 0.20, "violations": [...]},
        "license_compliance":   {"score": 60, "weight": 0.30, "violations": [...]},
        "performance":          {"score": 82, "weight": 0.20, "violations": [...]},
        "accessibility":        {"score": 70, "weight": 0.15, "violations": [...]},
        "developer_experience": {"score": 90, "weight": 0.15, "violations": [...]},
      }
    }
    """
    b_score, b_viol = brand_consistency_score(scan, approved_fonts=user_fonts)
    l_score, l_viol = license_compliance_score(scan, user_fonts)
    p_score, p_viol = performance_score(lighthouse)
    a_score, a_viol = accessibility_score(a11y)
    d_score, d_viol = developer_experience_score(scan, lighthouse)

    breakdown = {
        "brand_consistency": {
            "score": b_score,
            "weight": WEIGHTS["brand_consistency"],
            "violations": b_viol,
        },
        "license_compliance": {
            "score": l_score,
            "weight": WEIGHTS["license_compliance"],
            "violations": l_viol,
        },
        "performance": {
            "score": p_score,
            "weight": WEIGHTS["performance"],
            "violations": p_viol,
        },
        "accessibility": {
            "score": a_score,
            "weight": WEIGHTS["accessibility"],
            "violations": a_viol,
        },
        "developer_experience": {
            "score": d_score,
            "weight": WEIGHTS["developer_experience"],
            "violations": d_viol,
        },
    }

    overall = sum(
        data["score"] * data["weight"]
        for data in breakdown.values()
    )

    return {
        "overall_score": round(overall, 1),
        "breakdown": breakdown,
    }
