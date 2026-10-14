"""
High-Performance HTTP Client with TLS Impersonation & On-Disk SHA1 HTML Caching.
Designed to bypass Cloudflare bot mitigation on luciferdonghua.in.
"""

import hashlib
import random
import time
from pathlib import Path
from typing import Optional, Dict

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

import httpx

from .config import (
    PRIMARY_DOMAIN,
    FALLBACK_DOMAINS,
    REQUEST_TIMEOUT,
    REQUEST_DELAY,
    MAX_RETRIES,
    BACKOFF_FACTOR,
    DEFAULT_HEADERS,
    CACHE_DIR,
    CACHE_ENABLED,
)


class HtmlCache:
    """Manages SHA-1 hashed HTML documents on disk to avoid re-scraping."""

    def __init__(self, cache_dir: Path = CACHE_DIR, enabled: bool = CACHE_ENABLED):
        self.cache_dir = cache_dir
        self.enabled = enabled
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, url: str) -> Path:
        url_hash = hashlib.sha1(url.strip().encode("utf-8")).hexdigest()
        return self.cache_dir / f"{url_hash}.html"

    def get(self, url: str) -> Optional[str]:
        if not self.enabled:
            return None
        path = self._get_path(url)
        if path.exists():
            try:
                return path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                return None
        return None

    def set(self, url: str, content: str) -> None:
        if not self.enabled or not content:
            return
        path = self._get_path(url)
        try:
            path.write_text(content, encoding="utf-8", errors="ignore")
        except Exception:
            pass


class LuciferHttpClient:
    """HTTP Client with Chrome TLS Impersonation for luciferdonghua.in."""

    def __init__(self, primary_domain: str = PRIMARY_DOMAIN):
        self.active_domain = primary_domain.rstrip("/")
        self.cache = HtmlCache()
        self._last_request_time = 0.0

        # curl_cffi session with chrome124 impersonation
        self._curl_session = None
        if HAS_CURL_CFFI:
            try:
                self._curl_session = curl_requests.Session(impersonate="chrome124")
            except Exception:
                try:
                    self._curl_session = curl_requests.Session(impersonate="chrome120")
                except Exception:
                    self._curl_session = None

        # httpx client fallback
        self._httpx_client = httpx.Client(
            timeout=REQUEST_TIMEOUT,
            headers=DEFAULT_HEADERS,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )

    def _polite_delay(self) -> None:
        if REQUEST_DELAY > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < REQUEST_DELAY:
                time.sleep(REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    def get(
        self,
        url: str,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        refresh: bool = False,
    ) -> Optional[str]:
        """Fetches an HTML document with disk caching and retries."""
        cache_key = url
        if params:
            import urllib.parse
            cache_key = f"{url}?{urllib.parse.urlencode(params)}"

        # 1. Check disk cache
        if not refresh:
            cached = self.cache.get(cache_key)
            if cached:
                return cached

        # 2. Outbound request
        req_headers = {**DEFAULT_HEADERS, **(headers or {})}

        for attempt in range(1, MAX_RETRIES + 1):
            self._polite_delay()

            # Strategy A: curl_cffi Chrome impersonation
            if self._curl_session:
                try:
                    resp = self._curl_session.get(
                        url,
                        params=params,
                        headers=req_headers,
                        timeout=REQUEST_TIMEOUT,
                    )
                    if resp.status_code == 200:
                        content = resp.text
                        self.cache.set(cache_key, content)
                        return content
                    elif resp.status_code == 404:
                        return None
                    elif resp.status_code in (429, 500, 502, 503, 504):
                        time.sleep((BACKOFF_FACTOR ** attempt) + random.uniform(0.1, 0.5))
                        continue
                except Exception:
                    pass

            # Strategy B: httpx client fallback
            try:
                resp = self._httpx_client.get(
                    url,
                    params=params,
                    headers=req_headers,
                )
                if resp.status_code == 200:
                    content = resp.text
                    self.cache.set(cache_key, content)
                    return content
                elif resp.status_code == 404:
                    return None
                elif resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep((BACKOFF_FACTOR ** attempt) + random.uniform(0.1, 0.5))
                    continue
            except Exception:
                time.sleep((BACKOFF_FACTOR ** attempt) + random.uniform(0.1, 0.5))

        return None
