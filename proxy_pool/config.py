"""Configuration for Auto-Refreshing Proxy Pool."""

from typing import List, Tuple
from pydantic import BaseModel, Field


class ProxyPoolConfig(BaseModel):
    """Proxy Pool configuration settings."""
    refresh_interval_minutes: int = Field(default=30)
    validation_workers: int = Field(default=35)
    connect_timeout_seconds: float = Field(default=3.5)
    target_timeout_seconds: float = Field(default=4.0)
    min_pool_size: int = Field(default=5)
    max_pool_size: int = Field(default=25)
    cache_file: str = Field(default="data/proxy_pool.json")
    max_consecutive_failures: int = Field(default=2)

    # Free high-uptime sources
    sources: List[Tuple[str, str]] = Field(
        default=[
            ("ProxyScrape SSL", "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=yes&anonymity=all"),
            ("Monosans 30min", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"),
            ("RoosterKid HTTPS", "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt"),
        ]
    )

    # Scraper validation targets
    validation_targets: List[str] = Field(
        default=[
            "https://www.1tube.org/api/search?query=batman",
            "https://hindilinks4u.church/?s=batman",
        ]
    )


config = ProxyPoolConfig()
