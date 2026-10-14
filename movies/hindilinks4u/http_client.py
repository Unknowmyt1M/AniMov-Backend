"""HTTP Client for Hindilinks4u Scraper using curl_cffi with impersonation."""

import time
import logging
from typing import Optional, Dict, Any
from curl_cffi import requests

from .config import config

logger = logging.getLogger(__name__)


class Hindilinks4uHttpClient:
    """Robust HTTP client with browser impersonation and retries."""

    def __init__(self):
        self.session = requests.Session(impersonate=config.impersonate_profile)
        self.headers = {
            "User-Agent": config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": config.base_url + "/",
        }

    def get(self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """Execute GET request with exponential backoff retry."""
        req_headers = self.headers.copy()
        if headers:
            req_headers.update(headers)

        last_error = None
        for attempt in range(config.max_retries):
            try:
                resp = self.session.get(
                    url,
                    params=params,
                    headers=req_headers,
                    timeout=config.timeout_seconds,
                    allow_redirects=True,
                )
                if resp.status_code == 200:
                    return resp
                if resp.status_code in (403, 429, 503):
                    wait_time = config.backoff_factor * (2 ** attempt)
                    logger.warning(f"HTTP {resp.status_code} for {url}, retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    return resp
            except Exception as e:
                last_error = e
                wait_time = config.backoff_factor * (2 ** attempt)
                logger.warning(f"Request failed for {url} ({e}), retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)

        if last_error:
            raise last_error
        raise RuntimeError(f"Failed to fetch {url} after {config.max_retries} attempts")
