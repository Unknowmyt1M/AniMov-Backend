"""Anikoto Anime Scraper Module

Production-grade independent scraper for Anikoto (anikoto.cz).
Features:
- Full search catalog and detail extraction
- Episode list extraction with Sub/Dub categorization
- Server resolution (Vidstream, Megaplay, HD-1)
- Automatic AES-256-CBC stream payload decryption for direct master HLS .m3u8
- Subtitles & Skip-time (intro/outro) extraction
- SQLite WAL mode caching & database persistence
- DNS poisoning / ISP bypass via DoH & CurlOpt.RESOLVE
"""

from .scraper import AnikotoScraper
from .models import (
    AnikotoSearchResult,
    AnikotoSeriesDetail,
    AnikotoEpisode,
    AnikotoServer,
    AnikotoStreamResult,
    AnikotoSubtitleTrack,
    AnikotoSkipData,
)

__all__ = [
    "AnikotoScraper",
    "AnikotoSearchResult",
    "AnikotoSeriesDetail",
    "AnikotoEpisode",
    "AnikotoServer",
    "AnikotoStreamResult",
    "AnikotoSubtitleTrack",
    "AnikotoSkipData",
]
