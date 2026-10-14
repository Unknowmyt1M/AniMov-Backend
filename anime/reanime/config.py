"""Configuration settings for ReAnime Scraper."""

from pathlib import Path
from typing import List

BASE_URL = "https://reanime.to"

REANIME_RESOLVE_IPS: List[str] = [
    "172.67.138.177",
    "104.21.65.7",
]

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://reanime.to/",
}

DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "reanime.db"
REQUEST_TIMEOUT = 25
