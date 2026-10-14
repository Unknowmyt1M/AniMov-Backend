"""Configuration settings for Anikage Anime Scraper."""

from pathlib import Path
from typing import Dict

BASE_URL = "https://anikage.cc"
API_BASE_URL = "https://anikage.cc/api/media/anime"

DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://anikage.cc/",
    "Origin": "https://anikage.cc",
}

REQUEST_TIMEOUT = 15
CACHE_DIR = Path("data/anikage")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
