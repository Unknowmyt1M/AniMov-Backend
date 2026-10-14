"""Validator module for testing proxy connectivity directly on scraper targets."""

import time
import logging
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests

from .config import config

logger = logging.getLogger(__name__)


class ProxyValidator:
    """Parallel validator for real scraper target connectivity and Cloudflare bypass."""

    def __init__(self):
        self.workers = config.validation_workers
        self.target_timeout = config.target_timeout_seconds

    def test_single_proxy(self, proxy_url: str) -> Optional[Dict[str, Any]]:
        """Validate a single proxy directly on scraper targets."""
        proxies = {"http": proxy_url, "https": proxy_url}

        # Test against target endpoints
        for target_url in config.validation_targets:
            t0 = time.time()
            try:
                s = requests.Session(impersonate="chrome124")
                r = s.get(target_url, proxies=proxies, timeout=self.target_timeout)
                if r.status_code == 200 and len(r.text) > 1000:
                    latency = round((time.time() - t0) * 1000)
                    target_name = target_url.split("/")[2]
                    return {
                        "proxy": proxy_url,
                        "https_ok": True,
                        "target_ok": True,
                        "target_passed": target_name,
                        "latency_ms": latency,
                    }
            except Exception:
                continue

        return None

    def validate_batch(self, proxies: List[str], max_to_test: int = 250) -> List[Dict[str, Any]]:
        """Validate candidate proxies in parallel and return verified alive ones."""
        candidates = proxies[:max_to_test]
        verified: List[Dict[str, Any]] = []

        logger.info(f"Validating {len(candidates)} candidate proxies with {self.workers} workers...")
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {executor.submit(self.test_single_proxy, p): p for p in candidates}
            for f in as_completed(futures):
                res = f.result()
                if res and res["target_ok"]:
                    verified.append(res)

        # Sort by lowest latency
        verified.sort(key=lambda x: x["latency_ms"])
        logger.info(f"Validation complete: {len(verified)} target-verified proxies found.")
        return verified
