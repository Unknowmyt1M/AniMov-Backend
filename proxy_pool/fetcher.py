"""Fetcher module for gathering fresh public proxies from open APIs."""

import urllib.request
import logging
from typing import List, Set

from .config import config

logger = logging.getLogger(__name__)


class ProxyFetcher:
    """Fetches and deduplicates proxies from remote free endpoints using robust HTTP."""

    def fetch_all(self) -> List[str]:
        """Fetch proxies from all configured sources and return unique URLs."""
        collected: Set[str] = set()

        for name, url in config.sources:
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    raw_text = resp.read().decode("utf-8", errors="ignore")
                    lines = [l.strip() for l in raw_text.splitlines() if l.strip() and not l.startswith("#")]
                    count = 0
                    for line in lines:
                        p = line
                        if not p.startswith("http://") and not p.startswith("https://"):
                            p = "http://" + p
                        if ":" in p and len(p.split(":")) >= 3:
                            collected.add(p)
                            count += 1
                    logger.info(f"Source '{name}': fetched {count} raw proxies")
            except Exception as e:
                logger.warning(f"Failed to fetch from '{name}': {e}")

        logger.info(f"Total deduplicated proxies collected: {len(collected)}")
        return list(collected)
