"""
utils/http_client.py — Shared HTTP client for all scanners and analyzers.

Uses a persistent session with browser-grade headers to avoid being blocked
by sites that check for bot-like requests.
"""

from __future__ import annotations

import time
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ─── Session setup ─────────────────────────────────────────────────────────────

def _make_session() -> requests.Session:
    session = requests.Session()

    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    })

    return session


_SESSION = _make_session()


# ─── Public API ────────────────────────────────────────────────────────────────

def fetch(url: str, timeout: int = 20) -> Optional[str]:
    """
    Fetch a URL and return its text content, or None on any error.
    Uses a shared session with browser-grade headers and automatic retries.
    """
    try:
        resp = _SESSION.get(url, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"[http_client] Failed to fetch {url}: {e}")
        return None


def fetch_bytes(
    url: str,
    timeout: int = 15,
    max_bytes: int = 5 * 1024 * 1024,
) -> Optional[bytes]:
    """
    Fetch a URL and return raw bytes (for binary files such as PDFs), or None on error.
    Streams the response and aborts if the download would exceed max_bytes.
    """
    try:
        resp = _SESSION.get(url, timeout=timeout, allow_redirects=True, stream=True)
        resp.raise_for_status()
        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_content(chunk_size=8192):
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                print(
                    f"[http_client] {url}: exceeds "
                    f"{max_bytes // 1024 // 1024} MB limit, skipping"
                )
                return None
        return b"".join(chunks)
    except Exception as e:
        print(f"[http_client] Failed to fetch bytes from {url}: {e}")
        return None


def fetch_with_timing(url: str, timeout: int = 20) -> tuple[Optional[str], float]:
    """
    Fetch a URL and return (text, elapsed_ms). Returns (None, 0.0) on error.
    """
    try:
        start = time.perf_counter()
        resp = _SESSION.get(url, timeout=timeout, allow_redirects=True)
        elapsed_ms = (time.perf_counter() - start) * 1000
        resp.raise_for_status()
        return resp.text, elapsed_ms
    except Exception as e:
        print(f"[http_client] Failed to fetch {url}: {e}")
        return None, 0.0
