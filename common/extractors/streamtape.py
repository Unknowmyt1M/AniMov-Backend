"""
StreamTape Video Stream Extractor.
Extracts direct playable stream links and metadata from StreamTape embeds.
Domains: streamtape.com, streamtape.net, streamta.pe, strcloud.link, strtape.tech.
"""

import re
import logging
from typing import Dict, Any, Optional
from curl_cffi import requests

logger = logging.getLogger("extractors.streamtape")

STREAMTAPE_DOMAINS = [
    "streamtape.com",
    "streamtape.net",
    "streamta.pe",
    "strcloud.link",
    "strtape.tech",
]


class StreamTapeExtractor:
    """Extractor for StreamTape video embeds."""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session(impersonate="chrome124")

    @staticmethod
    def can_handle(url: str) -> bool:
        """Check if URL belongs to any StreamTape domain."""
        low = url.lower()
        return any(d in low for d in STREAMTAPE_DOMAINS)

    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """Extract StreamTape video ID from URL."""
        m = re.search(r"/(?:e|v)/([a-zA-Z0-9_-]+)", url, re.IGNORECASE)
        if m:
            return m.group(1)
        return None

    def extract(self, embed_url: str, referer: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract direct video stream link from StreamTape embed.

        :param embed_url: StreamTape embed URL
        :param referer: Optional referring URL
        :return: Dict containing direct stream URL, poster, and metadata
        """
        url = embed_url.strip()
        video_id = self.extract_video_id(url)
        if not video_id:
            raise ValueError(f"Could not extract StreamTape video ID from URL: {embed_url}")

        domain_match = re.search(r"https?://[^/]+", url)
        base_domain = domain_match.group(0) if domain_match else "https://streamtape.com"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": referer or url,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        # Strategy 1: High-Speed Direct HTML + robotlink DOM parsing
        try:
            page_url = f"{base_domain}/e/{video_id}"
            res = self.session.get(page_url, headers=headers, timeout=12)
            if res.status_code == 200:
                html_text = res.text

                # Extract title and poster
                title_m = re.search(r"<title>(.*?)</title>", html_text, re.IGNORECASE)
                title = title_m.group(1).replace("Watch ", "").strip() if title_m else f"StreamTape {video_id}"

                poster_m = re.search(r'poster\s*=\s*["\']([^"\']+)["\']', html_text)
                poster = poster_m.group(1) if poster_m else None

                # Extract robotlink/ideoooolink concatenation in JS
                # Pattern: document.getElementById('robotlink').innerHTML = '...' + ('...')
                m_tokens = re.search(
                    r"document\.getElementById\(['\"](?:robotlink|ideoooolink)['\"]\)\.innerHTML\s*=\s*['\"]([^'\"]+)['\"]\s*\+\s*['\"]?([^'\";\s\)]+)['\"]?",
                    html_text,
                )

                stream_url = None
                if m_tokens:
                    part1, part2 = m_tokens.groups()
                    part1 = part1.strip()
                    part2 = part2.strip().strip("'\"()")
                    full_link = part1 + part2
                    if full_link.startswith("//"):
                        stream_url = f"https:{full_link}"
                    elif not full_link.startswith("http"):
                        stream_url = f"https://{full_link.lstrip('/')}"
                    else:
                        stream_url = full_link

                # Alternative pattern: substring slice manipulation
                if not stream_url:
                    m_alt = re.search(
                        r"document\.getElementById\(['\"](?:robotlink|ideoooolink)['\"]\)\.innerHTML\s*=\s*['\"]([^'\"]+)['\"]",
                        html_text,
                    )
                    if m_alt:
                        raw = m_alt.group(1)
                        stream_url = f"https:{raw}" if raw.startswith("//") else raw

                if stream_url and "get_video" in stream_url:
                    return {
                        "server": "StreamTape",
                        "video_id": video_id,
                        "title": title,
                        "poster": poster,
                        "master_m3u8": None,
                        "direct_sources": [
                            {
                                "quality": "default",
                                "url": stream_url,
                                "type": "video/mp4",
                            }
                        ],
                        "headers": {"Referer": page_url},
                    }
        except Exception as e:
            logger.warning(f"Direct StreamTape token extraction failed for {video_id}: {e}. Trying yt-dlp fallback...")

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

                direct_sources = []
                for f in formats:
                    f_url = f.get("url", "")
                    if f_url and f.get("vcodec") != "none":
                        direct_sources.append({
                            "quality": f.get("format_note") or f"{f.get('height')}p" if f.get("height") else "video",
                            "url": f_url,
                            "ext": f.get("ext", "mp4"),
                        })

                return {
                    "server": "StreamTape",
                    "video_id": video_id,
                    "title": info.get("title"),
                    "poster": info.get("thumbnail"),
                    "duration": info.get("duration"),
                    "master_m3u8": None,
                    "direct_sources": direct_sources,
                    "headers": {"Referer": url},
                }
        except Exception as e:
            logger.error(f"yt-dlp fallback failed for StreamTape {video_id}: {e}")
            raise RuntimeError(f"Failed to extract StreamTape stream for {video_id}: {e}")
