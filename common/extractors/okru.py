"""
OK.ru (Odnoklassniki) Stream Extractor.
Extracts direct master HLS .m3u8 stream, progressive video sources, and metadata
from OK.ru embed or watch URLs (ok.ru/videoembed/... or ok.ru/video/...).

Uses high-speed direct HTML metadata parsing (150-350ms) with seamless yt-dlp fallback.
"""

import re
import json
import html
import logging
from typing import Dict, Any, Optional, List
from curl_cffi import requests

logger = logging.getLogger("extractors.okru")


class OkRuExtractor:
    """Extractor for OK.ru video embeds and watch URLs."""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session(impersonate="chrome124")

    @staticmethod
    def can_handle(url: str) -> bool:
        """Check if URL is an OK.ru player or embed URL."""
        low = url.lower()
        return "ok.ru" in low or "odnoklassniki.ru" in low

    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """
        Extract OK.ru video ID from embed or watch URL formats.
        Examples:
            - https://ok.ru/videoembed/15855292975668?nochat=1 -> 15855292975668
            - https://ok.ru/video/15855292975668 -> 15855292975668
            - https://ok.ru/dk?cmd=videoPlayerMetadata&mid=15855292975668 -> 15855292975668
        """
        # 1. /videoembed/15855292975668
        m_embed = re.search(r"/videoembed/([0-9]+)", url, re.IGNORECASE)
        if m_embed:
            return m_embed.group(1)

        # 2. /video/15855292975668
        m_watch = re.search(r"/video/([0-9]+)", url, re.IGNORECASE)
        if m_watch:
            return m_watch.group(1)

        # 3. mid=15855292975668
        m_mid = re.search(r"[?&]mid=([0-9]+)", url, re.IGNORECASE)
        if m_mid:
            return m_mid.group(1)

        return None

    def extract(self, embed_or_watch_url: str, referer: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract direct HLS .m3u8 link and metadata from OK.ru.

        :param embed_or_watch_url: Embed or watch URL
        :param referer: Optional referring page
        :return: Dict containing 'master_m3u8', 'direct_sources', 'title', etc.
        """
        video_id = self.extract_video_id(embed_or_watch_url)
        if not video_id:
            raise ValueError(f"Could not extract OK.ru video ID from URL: {embed_or_watch_url}")

        # Strategy 1: High-Speed Direct HTML / data-options Extraction (~200ms)
        try:
            embed_url = f"https://ok.ru/videoembed/{video_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Referer": referer or "https://ok.ru/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            res = self.session.get(embed_url, headers=headers, timeout=10)
            if res.status_code == 200:
                html_text = res.text
                match = re.search(r'data-options="([^"]+)"', html_text)
                if match:
                    raw_json = html.unescape(match.group(1))
                    data = json.loads(raw_json)
                    flashvars = data.get("flashvars", {})
                    metadata = flashvars.get("metadata", {})

                    movie = metadata.get("movie", {})
                    title = movie.get("title") or f"OK.ru {video_id}"
                    duration = movie.get("duration")
                    poster = movie.get("poster") or data.get("poster")

                    master_m3u8 = metadata.get("hlsManifestUrl")
                    direct_sources: List[Dict[str, Any]] = []

                    videos = metadata.get("videos", [])
                    if isinstance(videos, list):
                        for v in videos:
                            if isinstance(v, dict) and v.get("url"):
                                direct_sources.append({
                                    "quality": v.get("name", "video"),
                                    "url": v["url"],
                                    "type": "video/mp4",
                                })

                    if master_m3u8 or direct_sources:
                        return {
                            "server": "OK.ru",
                            "video_id": video_id,
                            "title": title,
                            "duration": duration,
                            "poster": poster,
                            "master_m3u8": master_m3u8,
                            "direct_sources": direct_sources,
                            "headers": {"Referer": "https://ok.ru/"},
                        }
        except Exception as e:
            logger.warning(f"Direct OK.ru extraction failed for {video_id}: {e}. Trying yt-dlp fallback...")

        # Strategy 2: Robust in-memory yt-dlp fallback
        try:
            import yt_dlp
            normalized_url = f"https://ok.ru/video/{video_id}"
            ydl_opts = {
                "quiet": True,
                "skip_download": True,
                "no_warnings": True,
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
                    "server": "OK.ru",
                    "video_id": video_id,
                    "title": info.get("title"),
                    "duration": info.get("duration"),
                    "poster": info.get("thumbnail"),
                    "master_m3u8": master_m3u8,
                    "direct_sources": direct_sources,
                    "headers": {"Referer": "https://ok.ru/"},
                }
        except Exception as e:
            logger.error(f"yt-dlp fallback failed for OK.ru {video_id}: {e}")
            raise RuntimeError(f"Failed to extract OK.ru stream for {video_id}: {e}")
