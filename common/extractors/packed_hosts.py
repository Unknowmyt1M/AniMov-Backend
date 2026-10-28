"""
Packed Hosts Stream Extractor.
De-obfuscates and extracts direct master HLS .m3u8 streams, progressive video sources,
and subtitles from Dean Edwards packed JavaScript hosts:
- VidHide / VidHidePRO / VidHideVIP / Yurn / FileLions
- StreamWish / WishFast / AllWish / VidWish / SeekPlayer
- FileMoon / MoonPlayer
- Vtbe / Waaw
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List
from curl_cffi import requests

from .unpacker import unpack_all, unpack_js, is_packed

logger = logging.getLogger("extractors.packed_hosts")


PACKED_DOMAINS = [
    "vidhide",
    "vidhidepro",
    "vidhidevip",
    "vidhidepre",
    "yurn",
    "filelions",
    "streamwish",
    "wishfast",
    "all-wish",
    "vidwish",
    "flaswish",
    "ajmidafast",
    "seekplayer",
    "filemoon",
    "moonplayer",
    "vtbe",
    "waaw",
    "netu",
]


class PackedHostExtractor:
    """Extractor for video hosts protected by Dean Edwards JavaScript packing."""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session(impersonate="chrome124")

    @staticmethod
    def can_handle(url: str) -> bool:
        """Check if URL belongs to any supported packed host domain."""
        low = url.lower()
        return any(domain in low for domain in PACKED_DOMAINS)

    @staticmethod
    def identify_server_name(url: str) -> str:
        """Identify human-readable host name from URL."""
        low = url.lower()
        if "vidhide" in low or "yurn" in low:
            return "VidHide"
        if "streamwish" in low or "wishfast" in low or "all-wish" in low or "vidwish" in low:
            return "StreamWish"
        if "filemoon" in low or "moonplayer" in low:
            return "FileMoon"
        if "filelions" in low:
            return "FileLions"
        if "vtbe" in low:
            return "Vtbe"
        if "waaw" in low or "netu" in low:
            return "Netu/Waaw"
        return "PackedHost"

    def extract(self, embed_url: str, referer: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract direct HLS .m3u8 link and metadata from a packed video host embed.

        :param embed_url: URL of the player embed (e.g. https://vidhide.com/v/XYZ)
        :param referer: Optional page referer
        :return: Dict containing 'master_m3u8', 'direct_sources', 'subtitles', etc.
        """
        server_name = self.identify_server_name(embed_url)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": referer or embed_url,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        # 1. Fetch embed page
        try:
            res = self.session.get(embed_url, headers=headers, timeout=15)
            if res.status_code != 200:
                raise RuntimeError(f"Host {server_name} returned HTTP {res.status_code}")
            html_text = res.text
        except Exception as e:
            logger.warning(f"Failed to fetch embed page from {embed_url}: {e}. Trying yt-dlp fallback...")
            return self._fallback_ytdlp(embed_url, server_name, referer)

        # 2. Deobfuscate scripts if packed
        scripts_to_search: List[str] = [html_text]
        if is_packed(html_text):
            unpacked_list = unpack_all(html_text)
            scripts_to_search.extend(unpacked_list)

        master_m3u8 = None
        direct_sources: List[Dict[str, Any]] = []
        poster = None
        subtitles: List[Dict[str, Any]] = []

        # 3. Search across all unpacked code blocks
        for text in scripts_to_search:
            # Poster image
            if not poster:
                img_m = re.search(r'image\s*:\s*["\']([^"\']+\.(?:jpe?g|png|webp)[^"\']*)["\']', text)
                if img_m:
                    poster = img_m.group(1).replace(r"\/", "/")

            # Direct JWPlayer sources block: sources: [{file: "...", ...}]
            sources_match = re.search(r'sources\s*:\s*(\[\s*\{.*?\}\s*\])', text, re.DOTALL)
            if sources_match:
                try:
                    raw_block = sources_match.group(1)
                    # Normalize single quotes and loose keys to valid JSON where possible
                    file_matches = re.findall(r'file\s*:\s*["\']([^"\']+)["\'](?:\s*,\s*label\s*:\s*["\']([^"\']+)["\'])?', raw_block)
                    for f_url, label in file_matches:
                        clean_url = f_url.replace(r"\/", "/")
                        if ".m3u8" in clean_url:
                            if not master_m3u8:
                                master_m3u8 = clean_url
                        else:
                            direct_sources.append({
                                "quality": label or "default",
                                "url": clean_url,
                                "type": "video/mp4",
                            })
                except Exception as e:
                    logger.debug(f"Failed parsing sources block: {e}")

            # Specific pattern: file: "https://...master.m3u8"
            if not master_m3u8:
                file_m3u8 = re.search(r'(?:file|source|src)\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', text)
                if file_m3u8:
                    master_m3u8 = file_m3u8.group(1).replace(r"\/", "/")

            # General regex search for .m3u8 URL
            if not master_m3u8:
                gen_m3u8 = re.search(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', text)
                if gen_m3u8:
                    master_m3u8 = gen_m3u8.group(0).replace(r"\/", "/")

            # Tracks (subtitles)
            tracks_match = re.findall(r'\{[^}]*file\s*:\s*["\']([^"\']+)["\'][^}]*label\s*:\s*["\']([^"\']+)["\']', text)
            for track_file, track_label in tracks_match:
                clean_track = track_file.replace(r"\/", "/")
                subtitles.append({"label": track_label, "url": clean_track})

            if master_m3u8:
                break

        if master_m3u8 or direct_sources:
            return {
                "server": server_name,
                "embed_url": embed_url,
                "master_m3u8": master_m3u8,
                "direct_sources": direct_sources,
                "poster": poster,
                "subtitles": subtitles,
                "headers": {"Referer": embed_url},
            }

        # 4. Fallback to yt-dlp if unpacking did not uncover stream
        logger.info(f"Unpacking found no streams for {embed_url}. Invoking yt-dlp fallback...")
        return self._fallback_ytdlp(embed_url, server_name, referer)

    def _fallback_ytdlp(self, embed_url: str, server_name: str, referer: Optional[str] = None) -> Dict[str, Any]:
        """Fallback stream extraction via yt-dlp."""
        try:
            import yt_dlp
            ydl_opts = {
                "quiet": True,
                "skip_download": True,
                "no_warnings": True,
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Referer": referer or embed_url,
                },
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(embed_url, download=False)
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
                    "server": server_name,
                    "embed_url": embed_url,
                    "title": info.get("title"),
                    "poster": info.get("thumbnail"),
                    "duration": info.get("duration"),
                    "master_m3u8": master_m3u8,
                    "direct_sources": direct_sources,
                    "subtitles": [],
                    "headers": {"Referer": embed_url},
                }
        except Exception as e:
            logger.error(f"yt-dlp fallback failed for {server_name} ({embed_url}): {e}")
            raise RuntimeError(f"Failed to extract packed stream from {embed_url}: {e}")
