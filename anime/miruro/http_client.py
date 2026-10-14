"""
Resilient HTTP client for Miruro Anime using curl_cffi with Cloudflare DoH resolution and disk caching.
"""
import time
import socket
import hashlib
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Dict, Any
from curl_cffi import requests
from curl_cffi.curl import CurlOpt

from .config import (
    CACHE_DIR,
    CACHE_TTL_HOURS,
    DEFAULT_HEADERS,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    MIRURO_CLOUDFLARE_IPS
)
from .decryptor import MiruroDecryptor


class HttpClient:
    def __init__(self, cache_enabled: bool = True, timeout: int = DEFAULT_TIMEOUT):
        self.cache_enabled = cache_enabled
        self.timeout = timeout
        
        # Build resolve options for Miruro domains
        resolve_list = []
        for host in ("www.miruro.cx", "miruro.cx"):
            for ip in MIRURO_CLOUDFLARE_IPS:
                resolve_list.extend([f"{host}:443:{ip}", f"{host}:80:{ip}"])

        self.session = requests.Session(
            impersonate="chrome124",
            curl_options={CurlOpt.RESOLVE: resolve_list}
        )

    def _get_cache_path(self, url: str) -> Path:
        key = hashlib.sha1(url.encode("utf-8")).hexdigest()
        return CACHE_DIR / f"{key}.bin"

    def _is_cache_valid(self, path: Path) -> bool:
        if not path.exists():
            return False
        age_seconds = time.time() - path.stat().st_mtime
        return age_seconds < (CACHE_TTL_HOURS * 3600)

    def get_bytes(self, url: str, headers: Optional[Dict[str, str]] = None, use_cache: bool = True) -> bytes:
        cache_path = self._get_cache_path(url)
        if self.cache_enabled and use_cache and self._is_cache_valid(cache_path):
            try:
                return cache_path.read_bytes()
            except Exception:
                pass

        req_headers = DEFAULT_HEADERS.copy()
        if headers:
            req_headers.update(headers)

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.session.get(
                    url,
                    headers=req_headers,
                    timeout=self.timeout
                )
                if response.status_code == 200:
                    content = response.content
                    if self.cache_enabled and use_cache and content:
                        try:
                            cache_path.write_bytes(content)
                        except Exception:
                            pass
                    return content
                elif response.status_code in (404, 410):
                    return b""
                else:
                    last_error = Exception(f"HTTP {response.status_code}: {response.text[:200]}")
            except Exception as e:
                last_error = e

            time.sleep(0.5 * attempt)

        raise last_error or Exception(f"Failed to fetch {url} after {MAX_RETRIES} attempts")

    def get_decoded_json(self, url: str, headers: Optional[Dict[str, str]] = None, use_cache: bool = True) -> Dict[str, Any]:
        """
        Fetches an API endpoint and decrypts Miruro's XOR-Gzip binary response into Python dictionary.
        """
        raw_bytes = self.get_bytes(url, headers=headers, use_cache=use_cache)
        if not raw_bytes:
            return {}
        return MiruroDecryptor.decode_catalog_payload(raw_bytes)
