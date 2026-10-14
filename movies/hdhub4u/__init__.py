"""HDHub4u Scraper package for dual-audio, 4K, 1080p movies and web series."""

from .scraper import HDHub4uScraper
from .models import (
    HDHub4uSearchResult,
    HDHub4uDetail,
    HDHub4uDownloadLink,
    HDHub4uEpisode,
)
from .http_client import HDHub4uHttpClient

__all__ = [
    "HDHub4uScraper",
    "HDHub4uHttpClient",
    "HDHub4uSearchResult",
    "HDHub4uDetail",
    "HDHub4uDownloadLink",
    "HDHub4uEpisode",
]
