"""
Rumble Stream Extractor.
Extracts direct master HLS .m3u8 stream, progressive video sources, and metadata
from Rumble embed or watch URLs (rumble.com/embed/... or rumble.com/v...).

Uses high-speed direct player API (100-300ms) with seamless yt-dlp fallback.
"""

import re
import logging
from typing import Dict, Any, Optional, List
from curl_cffi import requests

logger = logging.getLogger("extractors.rumble")


class RumbleExtractor:
    """Extractor for Rumble video embeds and watch URLs."""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session(impersonate="chrome124")

    @staticmethod
    def can_handle(url: str) -> bool:
        """Check if URL is a Rumble player or embed URL."""
        return "rumble.com" in url.lower()

    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """
        Extract Rumble video ID from embed or watch URL formats.
        Examples:
            - https://rumble.com/embed/v7dvlfe/?pub=4qfz5q -> v7dvlfe
            - https://rumble.com/embed/v7dvlfe/ -> v7dvlfe
            - https://rumble.com/v7dvlfe-renegade-ep-160.html -> v7dvlfe
            - https://rumble.com/v7dvlfe -> v7dvlfe
        """
        # 1. /embed/v7dvlfe
        m_embed = re.search(r"/embed/([a-zA-Z0-9]+)", url, re.IGNORECASE)
        if m_embed:
            return m_embed.group(1)

        # 2. /v7dvlfe-slug.html or /v7dvlfe
        m_watch = re.search(r"/v([a-zA-Z0-9]+)(?:-[^/?#]+)?(?:\.html)?", url, re.IGNORECASE)
        if m_watch:
            return f"v{m_watch.group(1)}"

        # 3. Query param ?v=v7dvlfe
        m_query = re.search(r"[?&]v=([a-zA-Z0-9]+)", url, re.IGNORECASE)
        if m_query:
            return m_query.group(1)

        return None

    def extract(self, embed_or_watch_url: str, referer: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract direct HLS .m3u8 link and metadata from Rumble.

        :param embed_or_watch_url: Embed or watch URL
        :param referer: Optional referring page
        :return: Dict containing 'master_m3u8', 'direct_sources', 'title', etc.
        """
        video_id = self.extract_video_id(embed_or_watch_url)
        if not video_id:
            raise ValueError(f"Could not extract Rumble video ID from URL: {embed_or_watch_url}")

        # Strategy 1: High-Speed Direct Player API (~100-300ms)
        try:
            api_url = f"https://rumble.com/embedJS/u3/?request=video&ver=2&v={video_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Referer": referer or f"https://rumble.com/embed/{video_id}/",
                "Accept": "application/json",
            }
            res = self.session.get(api_url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                title = data.get("title") or f"Rumble {video_id}"
                duration = data.get("duration")
                poster = data.get("i")
                author = data.get("author", {}).get("name")

                u_block = data.get("u", {})
                master_m3u8 = None
                direct_sources: List[Dict[str, Any]] = []

                # Extract HLS Master
                hls_info = u_block.get("hls")
                if isinstance(hls_info, dict):
                    master_m3u8 = hls_info.get("url")
                elif isinstance(hls_info, str):
                    master_m3u8 = hls_info

                # Extract MP4 Progressive Qualities
                mp4_block = u_block.get("mp4", {})
                if isinstance(mp4_block, dict):
                    for q_name, q_info in mp4_block.items():
                        if isinstance(q_info, dict) and q_info.get("url"):
                            meta = q_info.get("meta", {})
                            direct_sources.append({
                                "quality": f"{q_name}p" if q_name.isdigit() else q_name,
                                "url": q_info["url"],
                                "width": meta.get("w"),
                                "height": meta.get("h"),
                                "bitrate": meta.get("bitrate"),
                                "type": "video/mp4",
                            })

                if master_m3u8 or direct_sources:
                    return {
                        "server": "Rumble",
                        "video_id": video_id,
                        "title": title,
                        "duration": duration,
                        "poster": poster,
                        "author": author,
                        "master_m3u8": master_m3u8,
                        "direct_sources": direct_sources,
                        "headers": {"Referer": "https://rumble.com/"},
                    }
        except Exception as e:
            logger.warning(f"Direct Rumble API failed for {video_id}: {e}. Trying yt-dlp fallback...")

        # Strategy 2: Robust in-memory yt-dlp fallback
        try:
            import yt_dlp
            normalized_url = f"https://rumble.com/embed/{video_id}/"
            ydl_opts = {
                "quiet": True,
                "skip_download": True,
                "no_warnings": True,
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Referer": "https://rumble.com/",
                },
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(normalized_url, download=False)
                formats = info.get("formats", [])

                master_m3u8 = None
                direct_sources: List[Dict[str, Any]] = []

                for f in formats:
                    url = f.get("url", "")
                    if f.get("protocol") in ("m3u8_native", "m3u8") or ".m3u8" in url:
                        if not master_m3u8:
                            master_m3u8 = url
                    elif url and f.get("vcodec") != "none":
                        direct_sources.append({
                            "quality": f.get("format_note") or f"{f.get('height')}p" if f.get("height") else "video",
                            "url": url,
                            "ext": f.get("ext", "mp4"),
                            "filesize": f.get("filesize"),
                        })

                return {
                    "server": "Rumble",
                    "video_id": video_id,
                    "title": info.get("title"),
                    "duration": info.get("duration"),
                    "poster": info.get("thumbnail"),
                    "author": info.get("uploader"),
                    "master_m3u8": master_m3u8,
                    "direct_sources": direct_sources,
                    "headers": {"Referer": "https://rumble.com/"},
                }
        except Exception as e:
            logger.error(f"yt-dlp fallback failed for Rumble {video_id}: {e}")
            raise RuntimeError(f"Failed to extract Rumble stream for {video_id}: {e}")
