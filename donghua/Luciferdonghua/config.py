"""
Configuration settings for Lucifer Donghua Scraper.
Manages domain auto-failover, TLS impersonation headers, paths, and caching.
"""

import os
from pathlib import Path
from typing import List

SCRAPER_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRAPER_DIR.parent.parent

# Domain Configuration
# luciferdonghua.in is the canonical active domain. luciferdonghua.com redirects to bouduy.com.
PRIMARY_DOMAIN = os.getenv("LUCIFER_DOMAIN", "https://luciferdonghua.in").rstrip("/")
FALLBACK_DOMAINS: List[str] = [
    "https://luciferdonghua.in",
    "https://luciferdonghua.com",
]

# Networking & Rate Limiting
REQUEST_TIMEOUT: float = float(os.getenv("LUCIFER_TIMEOUT", "20.0"))
REQUEST_DELAY: float = float(os.getenv("LUCIFER_DELAY", "0.2"))
MAX_RETRIES: int = int(os.getenv("LUCIFER_MAX_RETRIES", "3"))
BACKOFF_FACTOR: float = 1.5

# Browser / TLS Impersonation Headers
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

# Storage & Cache Directories
CACHE_DIR = SCRAPER_DIR / "cache"
CACHE_ENABLED: bool = os.getenv("LUCIFER_CACHE_ENABLED", "1").lower() in ("1", "true", "yes")

DATA_DIR = SCRAPER_DIR / "data"
DATABASE_PATH = DATA_DIR / "lucifer.db"
OUTPUT_DIR = SCRAPER_DIR / "output"

DEFAULT_CONCURRENCY: int = int(os.getenv("LUCIFER_CONCURRENCY", "4"))

CACHE_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
