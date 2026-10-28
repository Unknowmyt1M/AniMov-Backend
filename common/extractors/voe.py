"""
Voe Video Stream Extractor.
Extracts direct master HLS .m3u8 stream and progressive links from Voe embeds.
Domains: voe.sx, voe-network.net, repackcloud.com, audaciousdefaulthousehold.com,
         20demidistance4orchestrating.com, turingcompletehouse.com.
"""

import re
import json
import base64
import codecs
import logging
from typing import Dict, Any, Optional, List
from curl_cffi import requests

logger = logging.getLogger("extractors.voe")

VOE_DOMAINS = [
    "voe.sx",
    "voe-network.net",
    "repackcloud.com",
    "audaciousdefaulthousehold.com",
    "20demidistance4orchestrating.com",
    "turingcompletehouse.com",
]


class VoeExtractor:
    """Extractor for Voe video embeds."""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session(impersonate="chrome124")

    @staticmethod
    def can_handle(url: str) -> bool:
        """Check if URL belongs to any Voe domain."""
        low = url.lower()
        return any(d in low for d in VOE_DOMAINS)

    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """Extract Voe video ID from URL."""
        m = re.search(r"/(?:e|v)/([a-zA-Z0-9]+)", url, re.IGNORECASE)
        if m:
            return m.group(1)
        return None

    def extract(self, embed_url: str, referer: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract direct HLS .m3u8 link and metadata from Voe embed.

        :param embed_url: Voe embed URL
        :param referer: Optional referring URL
        :return: Dict containing master_m3u8, direct_sources, poster, etc.
        """
        url = embed_url.strip()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": referer or url,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        # Strategy 1: Fetch HTML & search for cleartext or base64/rot13 encoded HLS
        try:
            res = self.session.get(url, headers=headers, timeout=12)
            if res.status_code == 200:
                html_text = res.text

                master_m3u8 = None
                poster = None

                # Search cleartext HLS
                # 1. 'hls': 'https://...m3u8'
                hls_m = re.search(r"['\"](?:hls|file)['\"]\s*:\s*['\"](https?://[^'\"]+\.m3u8[^'\"]*)['\"]", html_text)
                if hls_m:
                    master_m3u8 = hls_m.group(1)

                # 2. General regex search for .m3u8
                if not master_m3u8:
                    gen_m = re.search(r"https?://[^\s'\"<>]+\.m3u8[^\s'\"<>]*", html_text)
                    if gen_m:
                        master_m3u8 = gen_m.group(0)

                # 3. Base64 encoded strings
                if not master_m3u8:
                    b64_matches = re.findall(r"['\"]([a-zA-Z0-9+/=]{40,})['\"]", html_text)
                    for candidate in b64_matches:
                        try:
                            decoded = base64.b64decode(candidate).decode("utf-8", errors="ignore")
                            if ".m3u8" in decoded:
                                m_url = re.search(r"https?://[^\s'\"<>]+\.m3u8[^\s'\"<>]*", decoded)
                                if m_url:
                                    master_m3u8 = m_url.group(0)
                                    break
                            # Also check ROT13
                            rot = codecs.decode(candidate, "rot_13")
                            if ".m3u8" in rot:
                                m_url = re.search(r"https?://[^\s'\"<>]+\.m3u8[^\s'\"<>]*", rot)
                                if m_url:
                                    master_m3u8 = m_url.group(0)
                                    break
                        except Exception:
                            continue

                # Poster
                poster_m = re.search(r'poster\s*:\s*["\']([^"\']+)["\']', html_text)
                if poster_m:
                    poster = poster_m.group(1)

                if master_m3u8:
                    return {
                        "server": "Voe",
                        "embed_url": url,
                        "master_m3u8": master_m3u8,
                        "poster": poster,
                        "headers": {"Referer": url},
                    }
        except Exception as e:
            logger.warning(f"Direct Voe extraction failed for {url}: {e}. Trying yt-dlp fallback...")

        # Strategy 2: In-Memory yt-dlp Fallback
        try:
            import yt_dlp
            ydl_opts = {
                "quiet": True,
                "skip_download": True,
                "no_warnings": True,
                "http_headers": headers,
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
                    "server": "Voe",
                    "embed_url": url,
                    "title": info.get("title"),
                    "poster": info.get("thumbnail"),
                    "duration": info.get("duration"),
                    "master_m3u8": master_m3u8,
                    "direct_sources": direct_sources,
                    "headers": {"Referer": url},
                }
        except Exception as e:
            logger.error(f"yt-dlp fallback failed for Voe ({url}): {e}")
            raise RuntimeError(f"Failed to extract Voe stream for {url}: {e}")
