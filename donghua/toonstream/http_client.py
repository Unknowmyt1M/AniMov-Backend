"""Resilient HTTP client for Toonstream Scraper."""

import logging
from typing import Dict, Any, Optional
import httpx

from .config import BASE_URL, DEFAULT_HEADERS, REQUEST_TIMEOUT, DOMAINS_JSON_URL

logger = logging.getLogger("toonstream.http_client")


class ToonstreamHttpClient:
    """HTTP Client with automatic domain resolution and resilient retries."""

    def __init__(self, timeout: int = REQUEST_TIMEOUT):
        self.timeout = timeout
        self.base_url = BASE_URL
        self._sync_active_domain()
        self.client = httpx.Client(
            headers=DEFAULT_HEADERS,
            timeout=self.timeout,
            follow_redirects=True,
        )

    def _sync_active_domain(self):
        """Optionally refresh the latest mirror from upstream domains.json."""
        try:
            with httpx.Client(timeout=5.0) as temp_client:
                r = temp_client.get(DOMAINS_JSON_URL)
                if r.status_code == 200:
                    domains = r.json()
                    active = domains.get("toonstream")
                    if active and active.startswith("http"):
                        self.base_url = active.rstrip("/")
                        logger.info(f"Synchronized Toonstream base URL: {self.base_url}")
        except Exception as e:
            logger.debug(f"Using default base URL ({self.base_url}): {e}")

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
        """Close underlying client session."""
        try:
            self.client.close()
        except Exception:
            pass
