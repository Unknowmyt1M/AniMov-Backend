"""
Resilient HTTP client using curl_cffi with TLS fingerprint impersonation and disk caching for AnimeKhor.
"""
import hashlib
import time
import socket
from urllib.parse import urlparse
from pathlib import Path
from typing import Optional, Dict, Any
from curl_cffi import requests
from curl_cffi.curl import CurlOpt

from .config import CACHE_DIR, CACHE_TTL_HOURS, DEFAULT_HEADERS, DEFAULT_TIMEOUT, MAX_RETRIES


class HttpClient:
    def __init__(self, cache_enabled: bool = True, timeout: int = DEFAULT_TIMEOUT):
        self.cache_enabled = cache_enabled
        self.timeout = timeout
        self.session = requests.Session(
            impersonate="chrome124",
            curl_options={CurlOpt.IPRESOLVE: 1}
        )

    def _get_cache_path(self, url: str) -> Path:
        key = hashlib.sha1(url.encode("utf-8")).hexdigest()
        return CACHE_DIR / f"{key}.html"

    def _is_cache_valid(self, path: Path) -> bool:
        if not path.exists():
            return False
        age_seconds = time.time() - path.stat().st_mtime
        return age_seconds < (CACHE_TTL_HOURS * 3600)

    def get(self, url: str, headers: Optional[Dict[str, str]] = None, use_cache: bool = True) -> str:
        cache_path = self._get_cache_path(url)
        if self.cache_enabled and use_cache and self._is_cache_valid(cache_path):
            try:
                return cache_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass

        req_headers = DEFAULT_HEADERS.copy()
        if headers:
            req_headers.update(headers)

        domain = urlparse(url).netloc
        try:
            socket.getaddrinfo(domain, 443, socket.AF_INET)
        except Exception:
            pass

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.session.get(
                    url,
                    headers=req_headers,
                    timeout=self.timeout
                )
                if response.status_code == 200:
                    html = response.text
                    if self.cache_enabled and use_cache:
                        try:
                            cache_path.write_text(html, encoding="utf-8", errors="replace")
                        except Exception:
                            pass
                    return html
                elif response.status_code in (404, 410):
                    raise ValueError(f"HTTP {response.status_code}: Resource not found at {url}")
                else:
                    last_error = RuntimeError(f"HTTP {response.status_code} on attempt {attempt}")
            except Exception as e:
                last_error = e
                try:
                    socket.getaddrinfo(domain, 443, socket.AF_INET)
                except Exception:
                    pass
                time.sleep(1.0 * attempt)

        raise RuntimeError(f"Failed to fetch {url} after {MAX_RETRIES} attempts. Cause: {last_error}")
