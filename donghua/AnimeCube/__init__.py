"""
AnimeCube Scraper Package
Next.js (React Server Components / RSC) Donghua Streaming Platform Crawler.
"""
from .scraper import AnimeCubeScraper
from .models import SeriesDetail, EpisodeDetail, EpisodeSummary, StreamServer, SearchResult, CrawlStats

__all__ = [
    "AnimeCubeScraper",
    "SeriesDetail",
    "EpisodeDetail",
    "EpisodeSummary",
    "StreamServer",
    "SearchResult",
    "CrawlStats",
]
