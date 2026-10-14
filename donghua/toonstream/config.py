"""Configuration settings for Toonstream Scraper."""

from pathlib import Path
from typing import List, Dict

# Primary domain & Fallbacks
BASE_URL = "https://toonstream.vip"
DOMAINS_JSON_URL = "https://raw.githubusercontent.com/phisher98/TVVVV/refs/heads/main/domains.json"

DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Referer": "https://toonstream.vip/",
}

REQUEST_TIMEOUT = 15
CACHE_DIR = Path("data/toonstream")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
