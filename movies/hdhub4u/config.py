"""Configuration settings for HDHub4u Scraper."""

from pathlib import Path
from typing import Dict

BASE_URL = "https://new7.hdhub4u.cl"
DOMAINS_JSON_URL = "https://raw.githubusercontent.com/phisher98/TVVVV/refs/heads/main/domains.json"

# Typesense search cluster used by HDHub4u
SEARCH_API_URL = "https://search.pingora.fyi/collections/post/documents/search"

DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Referer": "https://new7.hdhub4u.cl/",
    "Origin": "https://new7.hdhub4u.cl",
}

REQUEST_TIMEOUT = 15
CACHE_DIR = Path("data/hdhub4u")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
