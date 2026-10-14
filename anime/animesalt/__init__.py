"""AnimeSalt Anime Scraper Module."""

from .scraper import AnimeSaltScraper
from .models import (
    AnimeSaltSearchResult,
    AnimeSaltSeriesDetail,
    AnimeSaltEpisode,
    AnimeSaltAudioStream,
)

__all__ = [
    "AnimeSaltScraper",
    "AnimeSaltSearchResult",
    "AnimeSaltSeriesDetail",
    "AnimeSaltEpisode",
    "AnimeSaltAudioStream",
]
