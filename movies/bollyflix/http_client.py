"""HTTP Client for BollyFlix with dynamic domain tracking and DoH resolution."""

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


class BollyflixHttpClient:
    """Robust HTTP client with dynamic domain resolution and DoH-assisted TLS impersonation."""

    def __init__(self):
        self.base_url = config.base_url
        self.resolve_rules: List[str] = []
        self._init_live_domain()
        self.session = self._create_session()

    def _init_live_domain(self):
        """Scrape bollyflix.nz tracker to get the current working Bollyflix domain."""
        tracker_domain = "bollyflix.nz"
        tracker_ips = resolve_doh_ips(tracker_domain) or ["104.21.0.228", "172.67.128.92"]
        resolves = [f"{tracker_domain}:443:{ip}" for ip in tracker_ips]

        for attempt in range(2):
            try:
                temp_session = requests.Session(
                    impersonate=config.impersonate_profile,
                    curl_options={CurlOpt.RESOLVE: resolves},
                )
                tracker_headers = {
                    "User-Agent": config.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Referer": "https://bollyflix.nz/",
                }
                res = temp_session.get(config.tracker_url, headers=tracker_headers, allow_redirects=False, timeout=6)
                if res.status_code in (301, 302, 307, 308):
                    location = res.headers.get("location")
                    if location:
                        live_domain = location.rstrip("/")
                        self.base_url = live_domain
                        config.base_url = live_domain
                        logger.info(f"Dynamically resolved BollyFlix live domain: {self.base_url}")
                        break
            except Exception as e:
                if attempt == 1:
                    logger.debug(f"Tracker check failed on attempt {attempt}: {e}. Retaining {self.base_url}")

        # Setup DoH for current active base domain
        parsed = urllib.parse.urlparse(self.base_url)
        live_host = parsed.netloc
        if live_host:
            live_ips = resolve_doh_ips(live_host) or ["104.21.16.156", "172.67.213.172"]
            for ip in live_ips:
                self.resolve_rules.extend([f"{live_host}:443:{ip}", f"{live_host}:80:{ip}"])

    def _create_session(self) -> requests.Session:
        curl_opts = {}
        if self.resolve_rules:
            curl_opts[CurlOpt.RESOLVE] = self.resolve_rules
        return requests.Session(
            impersonate=config.impersonate_profile,
            curl_options=curl_opts,
        )

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "User-Agent": config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": self.base_url + "/",
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
                err_str = str(e).lower()
                if any(k in err_str for k in ["could not resolve host", "connection was reset", "ssl", "dns", "unreachable"]):
                    # Refresh live domain once on hard network fail
                    logger.warning(f"Network error on {url}, re-resolving live domain...")
                    self._init_live_domain()
                    self.session = self._create_session()
                wait_time = config.backoff_factor * (2 ** attempt)
                logger.warning(f"Request failed for {url} ({e}), retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)

        if last_error:
            raise ConnectionError(f"Failed to connect to BollyFlix ({url}): {last_error}")
        raise RuntimeError(f"Failed to fetch {url} after {config.max_retries} attempts")
