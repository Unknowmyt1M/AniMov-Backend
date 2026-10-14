"""Configuration settings for WatchAnimeWorld Scraper."""

from pathlib import Path
from typing import List

BASE_URL = "https://watchanimeworld.one"

WATCHANIMEWORLD_RESOLVE_IPS: List[str] = [
    "172.67.205.170",
    "104.21.15.91",
]

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://watchanimeworld.one/",
}

DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "watchanimeworld.db"
REQUEST_TIMEOUT = 15
