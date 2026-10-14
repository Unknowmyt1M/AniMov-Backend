"""
Configuration and constants for the Miruro Anime scraper.
"""
from pathlib import Path

# Domains
MIRURO_LANDING = "https://www.miruro.com"
PRIMARY_DOMAIN = "https://www.miruro.cx"
API_BASE = f"{PRIMARY_DOMAIN}/api/v1"

# Obfuscation & Crypto Keys
CATALOG_XOR_KEY = b"miruro/catalog"
PROXY_OBF_KEY = bytes.fromhex("a54d389c18527d9fd3e7f0643e27edbe")

# Known Cloudflare IPv4 fallbacks for Miruro (used when local DNS is poisoned/blocked)
MIRURO_CLOUDFLARE_IPS = ["104.21.88.155", "172.67.185.198"]

# Storage & Cache Paths
MODULE_DIR = Path(__file__).parent.resolve()
DATA_DIR = MODULE_DIR / "data"
CACHE_DIR = MODULE_DIR / "cache"
OUTPUT_DIR = MODULE_DIR / "output"

for d in (DATA_DIR, CACHE_DIR, OUTPUT_DIR):
    d.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "miruro.db"

# Request Settings
DEFAULT_TIMEOUT = 15
CACHE_TTL_HOURS = 24
MAX_RETRIES = 3

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Referer": f"{PRIMARY_DOMAIN}/",
    "Origin": PRIMARY_DOMAIN,
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin"
}
