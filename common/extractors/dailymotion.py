"""
Dailymotion Stream Extractor.
Extracts direct master HLS .m3u8 stream, progressive video sources, and subtitles
from Dailymotion embed or watch URLs (geo.dailymotion.com / dailymotion.com).

Uses high-speed direct metadata API (80-200ms) with seamless yt-dlp fallback.
"""

import re
import logging
from typing import Dict, Any, Optional, List
from curl_cffi import requests

logger = logging.getLogger("extractors.dailymotion")


class DailymotionExtractor:
    """Extractor for Dailymotion video embeds and player URLs."""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session(impersonate="chrome124")

    @staticmethod
    def can_handle(url: str) -> bool:
        """Check if URL is a Dailymotion player or embed URL."""
        low = url.lower()
        return "dailymotion.com" in low or "dai.ly" in low

    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """Extract Dailymotion video ID from various embed and watch URL formats."""
        # 1. geo.dailymotion.com/player/...html?video=k4wD3bgoXxbXrVM5AaC
        m_query = re.search(r"video=([a-zA-Z0-9]+)", url)
        if m_query:
            return m_query.group(1)

        # 2. dailymotion.com/embed/video/k42LYHJBnNf8NCIyyk6 or /video/k42LYHJBnNf8NCIyyk6
        m_path = re.search(r"/video/([a-zA-Z0-9]+)", url)
        if m_path:
            return m_path.group(1)

        # 3. dai.ly/k42LYHJBnNf8NCIyyk6
        m_short = re.search(r"dai\.ly/([a-zA-Z0-9]+)", url)
        if m_short:
            return m_short.group(1)

        return None

    def extract(self, embed_or_watch_url: str, referer: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract direct HLS .m3u8 link and metadata from Dailymotion.

        :param embed_or_watch_url: Embed or watch URL
        :param referer: Optional referring page
        :return: Dict containing 'master_m3u8', 'direct_sources', 'subtitles', etc.
        """
        video_id = self.extract_video_id(embed_or_watch_url)
        if not video_id:
            raise ValueError(f"Could not extract Dailymotion video ID from URL: {embed_or_watch_url}")

        # Strategy 1: High-Speed Direct Metadata API (~200ms)
        try:
            metadata_url = f"https://www.dailymotion.com/player/metadata/video/{video_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Referer": referer or "https://geo.dailymotion.com/",
                "Accept": "application/json",
            }
            res = self.session.get(metadata_url, headers=headers, timeout=8)
            if res.status_code == 200:
                data = res.json()
                title = data.get("title") or f"Dailymotion {video_id}"
                duration = data.get("duration")
                poster = data.get("posters", {}).get("60") or data.get("filmstrip", {}).get("template_url")

                qualities = data.get("qualities", {})
                master_m3u8 = None
                direct_sources: List[Dict[str, Any]] = []

                # Extract master HLS stream
                auto_list = qualities.get("auto", [])
                for item in auto_list:
                    if item.get("type") in ("application/x-mpegURL", "application/vnd.apple.mpegurl") or ".m3u8" in item.get("url", ""):
                        master_m3u8 = item.get("url")
                        break

                # Extract progressive qualities if present
                for q_label, stream_items in qualities.items():
                    if q_label == "auto":
                        continue
                    if isinstance(stream_items, list):
                        for s in stream_items:
                            direct_sources.append({
                                "quality": f"{q_label}p" if q_label.isdigit() else q_label,
                                "url": s.get("url"),
                                "type": s.get("type", "video/mp4"),
                            })

                # Subtitles
                subtitles: List[Dict[str, Any]] = []
                sub_data = data.get("subtitles", {}).get("data", {})
                if isinstance(sub_data, dict):
                    for lang_code, s_info in sub_data.items():
                        if isinstance(s_info, dict) and s_info.get("urls"):
                            subtitles.append({
                                "lang": lang_code,
                                "label": s_info.get("label", lang_code.upper()),
                                "url": s_info["urls"][0],
                            })

                if master_m3u8 or direct_sources:
                    return {
                        "server": "Dailymotion",
                        "video_id": video_id,
                        "title": title,
                        "duration": duration,
                        "poster": poster,
                        "master_m3u8": master_m3u8,
                        "direct_sources": direct_sources,
                        "subtitles": subtitles,
                        "headers": {"Referer": "https://www.dailymotion.com/"},
                    }
        except Exception as e:
            logger.warning(f"Direct Dailymotion metadata API failed for {video_id}: {e}. Trying yt-dlp fallback...")

        # Strategy 2: Robust in-memory yt-dlp fallback
        try:
            import yt_dlp
            normalized_url = f"https://www.dailymotion.com/video/{video_id}"
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
                    "server": "Dailymotion",
                    "video_id": video_id,
                    "title": info.get("title"),
                    "duration": info.get("duration"),
                    "poster": info.get("thumbnail"),
                    "master_m3u8": master_m3u8,
                    "direct_sources": direct_sources,
                    "subtitles": [],
                    "headers": {"Referer": "https://www.dailymotion.com/"},
                }
        except Exception as e:
            logger.error(f"yt-dlp fallback failed for Dailymotion {video_id}: {e}")
            raise RuntimeError(f"Failed to extract Dailymotion stream for {video_id}: {e}")
