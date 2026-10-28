"""
Universal Stream Extractor Package for AniMov Backend.

Provides dedicated extractors and a unified dispatch resolver (`resolve_stream_url`)
for all primary streaming players, embed hosts, and packed JavaScript video servers:
- Dailymotion (geo.dailymotion.com / dailymotion.com)
- Rumble (rumble.com/embed)
- OK.ru (ok.ru/videoembed)
- Zephyrix / MultiCloud / Ravok (play.zephyrix.org / ravok.buzz)
- Abyss / DubPlayer (player.abyssplayer.com)
- Packed Hosts (VidHide, StreamWish, WishFast, FileMoon, FileLions, Vtbe, Waaw)
"""

import logging
from typing import Dict, Any, Optional

from .unpacker import unpack_js, unpack_all, is_packed
from .zephyrix import ZephyrixExtractor
from .abyss import AbyssExtractor
from .dailymotion import DailymotionExtractor
from .rumble import RumbleExtractor
from .okru import OkRuExtractor
from .packed_hosts import PackedHostExtractor

logger = logging.getLogger("extractors")


def resolve_stream_url(embed_url: str, referer: Optional[str] = None) -> Dict[str, Any]:
    """
    Automatically detect player / host family from embed URL and extract
    direct HLS master .m3u8, video sources, subtitles, and metadata.

    :param embed_url: The iframe or embed URL to resolve
    :param referer: Optional referer header
    :return: Dict containing extracted stream URLs and metadata
    """
    if not embed_url or not embed_url.strip():
        raise ValueError("Empty or invalid URL provided")

    url = embed_url.strip()
    low = url.lower()

    # 1. Dailymotion
    if DailymotionExtractor.can_handle(url):
        logger.info(f"Resolving via DailymotionExtractor: {url}")
        return DailymotionExtractor().extract(url, referer=referer)

    # 2. Rumble
    if RumbleExtractor.can_handle(url):
        logger.info(f"Resolving via RumbleExtractor: {url}")
        return RumbleExtractor().extract(url, referer=referer)

    # 3. OK.ru
    if OkRuExtractor.can_handle(url):
        logger.info(f"Resolving via OkRuExtractor: {url}")
        return OkRuExtractor().extract(url, referer=referer)

    # 4. Zephyrix / MultiCloud / Ravok
    if any(h in low for h in ["zephyrix", "zephyrflick", "ravok"]):
        logger.info(f"Resolving via ZephyrixExtractor: {url}")
        return ZephyrixExtractor().extract(url, referer=referer or "https://watchanimeworld.one/")

    # 5. Abyss / DubPlayer
    if any(h in low for h in ["abyssplayer", "dub-player"]):
        logger.info(f"Resolving via AbyssExtractor: {url}")
        return AbyssExtractor().extract(url, referer=referer or "https://watchanimeworld.one/")

    # 6. Packed Hosts (VidHide, StreamWish, FileMoon, FileLions, etc.)
    if PackedHostExtractor.can_handle(url):
        logger.info(f"Resolving via PackedHostExtractor: {url}")
        return PackedHostExtractor().extract(url, referer=referer)

    # 7. Generic Fallback via yt-dlp
    logger.info(f"Unknown host family for {url}. Attempting generic yt-dlp extraction...")
    try:
        import yt_dlp
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "no_warnings": True,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Referer": referer or url,
            },
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])

            master_m3u8 = None
            direct_sources = []

            for f in formats:
                f_url = f.get("url", "")
                if f.get("protocol") in ("m3u8_native", "m3u8") or ".m3u8" in f_url:
                    if not master_m3u8:
                        master_m3u8 = f_url
                elif f_url and f.get("vcodec") != "none":
                    direct_sources.append({
                        "quality": f.get("format_note") or f"{f.get('height')}p" if f.get("height") else "video",
                        "url": f_url,
                        "ext": f.get("ext", "mp4"),
                    })

            return {
                "server": info.get("extractor_key", "Generic"),
                "embed_url": url,
                "title": info.get("title"),
                "poster": info.get("thumbnail"),
                "duration": info.get("duration"),
                "master_m3u8": master_m3u8,
                "direct_sources": direct_sources,
                "headers": {"Referer": url},
            }
    except Exception as e:
        logger.error(f"Generic resolver failed for {url}: {e}")
        raise ValueError(f"No extractor available and generic fallback failed for URL: {url} ({e})")


__all__ = [
    "unpack_js",
    "unpack_all",
    "is_packed",
    "ZephyrixExtractor",
    "AbyssExtractor",
    "DailymotionExtractor",
    "RumbleExtractor",
    "OkRuExtractor",
    "PackedHostExtractor",
    "resolve_stream_url",
]
