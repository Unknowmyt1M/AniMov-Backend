"""HTTP Client for Hindilinks4u Scraper using curl_cffi with impersonation and DoH resolution."""

import time
import json
import logging
import urllib.parse
import urllib.request
from typing import Optional, Dict, Any, List
from curl_cffi import requests, CurlOpt

from .config import config

logger = logging.getLogger(__name__)


def resolve_doh_ips(domain: str) -> List[str]:
    """Resolve A records using Google DoH to bypass ISP DNS poisoning."""
    try:
        url = f"https://dns.google/resolve?name={domain}&type=A"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read())
            return [a["data"] for a in data.get("Answer", []) if a.get("type") == 1]
    except Exception as e:
        logger.debug(f"DoH resolution failed for {domain}: {e}")
        return []


class Hindilinks4uHttpClient:
    """Robust HTTP client with browser impersonation, DoH resolution, and retries."""

    def __init__(self):
        parsed = urllib.parse.urlparse(config.base_url)
        domain = parsed.netloc
        ips = resolve_doh_ips(domain) or ["172.67.160.68", "104.21.9.157"]
        resolves = [f"{domain}:443:{ip}" for ip in ips]

        self.session = requests.Session(
            impersonate=config.impersonate_profile,
            curl_options={CurlOpt.RESOLVE: resolves} if resolves else {},
        )
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
