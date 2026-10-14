"""
AnimeKhor Scraper Package
"""
from .scraper import AnimeKhorScraper
from .models import SeriesDetail, EpisodeDetail, EpisodeSummary, StreamServer, DownloadOption, SearchResult, CrawlStats

__all__ = [
    "AnimeKhorScraper",
    "SeriesDetail",
    "EpisodeDetail",
    "EpisodeSummary",
    "StreamServer",
    "DownloadOption",
    "SearchResult",
    "CrawlStats",
]
