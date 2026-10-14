"""AnimeSuge Anime Scraper Module."""

from .scraper import AnimeSugeScraper
from .models import (
    AnimeSugeSearchResult,
    AnimeSugeSeriesDetail,
    AnimeSugeEpisode,
    AnimeSugeServer,
    AnimeSugeStreamResult,
)

__all__ = [
    "AnimeSugeScraper",
    "AnimeSugeSearchResult",
    "AnimeSugeSeriesDetail",
    "AnimeSugeEpisode",
    "AnimeSugeServer",
    "AnimeSugeStreamResult",
]
