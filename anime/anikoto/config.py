"""Configuration settings for Anikoto Scraper."""

from pathlib import Path
from typing import List

# Base domains
BASE_URL = "https://anikoto.cz"
EMBED_BASE_URL = "https://megaplay.buzz"

# Fallback known Cloudflare Anycast IPs to bypass Indian ISP DNS blocks
ANIKOTO_RESOLVE_IPS: List[str] = [
    "104.21.53.70",
    "172.67.209.174",
]

MEGAPLAY_RESOLVE_IPS: List[str] = [
    "172.67.196.5",
    "104.21.21.28",
]

# Google DoH URL
DOH_URL = "https://dns.google/resolve"

# Decryption Seeds for MegaPlay stream sources
MEGAPLAY_KEY_SEED = "i?LMTAx0Q6,:}50U"
MEGAPLAY_IV_SEED = "W0;27ToaUpl_P%'c"

# Request Headers
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://anikoto.cz/",
}

AJAX_HEADERS = {
    **DEFAULT_HEADERS,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

# Storage paths
DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "anikoto.db"

REQUEST_TIMEOUT = 15
CACHE_TTL = 3600  # 1 hour
