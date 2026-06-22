"""
extractor/ — Playwright-based browser font extraction.

Ported from the JS brand-consistency-analyzer project.
Uses a real headless browser to read computed styles (what actually renders)
rather than parsing CSS source (which misses cascade, inheritance, and fallbacks).

This module is OPTIONAL — if Playwright is not installed, the scoring engine
falls back to the HTTP-based scanner data.
"""

from .extractor import extract_site, extract_page

__all__ = ["extract_site", "extract_page"]
