"""Resilient HTTP client for Anikage Anime Scraper."""

import logging
from typing import Dict, Any, Optional
import httpx

from .config import BASE_URL, DEFAULT_HEADERS, REQUEST_TIMEOUT

logger = logging.getLogger("anikage.http_client")


class AnikageHttpClient:
    """HTTP Client for Anikage REST API."""

    def __init__(self, timeout: int = REQUEST_TIMEOUT):
        self.timeout = timeout
        self.base_url = BASE_URL
        self.client = httpx.Client(
            headers=DEFAULT_HEADERS,
            timeout=self.timeout,
            follow_redirects=True,
        )

    def get(
        self,
        url_or_path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Fetch URL or relative path with retries."""
        if url_or_path.startswith("http"):
            full_url = url_or_path
        else:
            full_url = f"{self.base_url}/{url_or_path.lstrip('/')}"

        req_headers = dict(DEFAULT_HEADERS)
        if headers:
            req_headers.update(headers)

        last_error = None
        for attempt in range(2):
            try:
                resp = self.client.get(full_url, params=params, headers=req_headers)
                if resp.status_code == 200:
                    return resp
                logger.warning(f"GET {full_url} returned HTTP {resp.status_code}")
            except Exception as e:
                last_error = e
                logger.warning(f"GET {full_url} failed attempt {attempt + 1}: {e}")

        if last_error:
            raise last_error
        raise RuntimeError(f"Failed to fetch {full_url} (HTTP {resp.status_code})")

    def close(self):
        """Close client session."""
        try:
            self.client.close()
        except Exception:
            pass
