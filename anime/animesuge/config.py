"""Configuration settings for AnimeSuge Scraper."""

from pathlib import Path
from typing import List

# Base domains
BASE_URL = "https://animesuge.cz"
EMBED_BASE_URL = "https://megaplay.buzz"

# Fallback known Cloudflare Anycast IPs to bypass local ISP DNS blocking
ANIMESUGE_RESOLVE_IPS: List[str] = [
    "104.21.91.146",
    "172.67.222.25",
]

MEGAPLAY_RESOLVE_IPS: List[str] = [
    "172.67.196.5",
    "104.21.21.28",
]

# Decryption Seeds for MegaPlay stream sources
MEGAPLAY_KEY_SEED = "i?LMTAx0Q6,:}50U"
MEGAPLAY_IV_SEED = "W0;27ToaUpl_P%'c"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://animesuge.cz/",
}

AJAX_HEADERS = {
    **DEFAULT_HEADERS,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "animesuge.db"
REQUEST_TIMEOUT = 15
