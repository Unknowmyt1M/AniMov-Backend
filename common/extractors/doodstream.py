"""
DoodStream / Dood / Playmogo Stream Extractor.
Extracts direct playable stream links and metadata from DoodStream embeds.
Domains: dood.to, dood.so, dood.la, dood.ws, dood.sh, doodstream.com,
         doods.pro, ds2play.com, dood.pm, dood.wf, dood.cx, playmogo.com, do0od.com.
"""

import re
import time
import string
import random
import logging
from typing import Dict, Any, Optional
from curl_cffi import requests

logger = logging.getLogger("extractors.doodstream")

DOOD_DOMAINS = [
    "dood.to",
    "dood.so",
    "dood.la",
    "dood.ws",
    "dood.sh",
    "doodstream.com",
    "doods.pro",
    "ds2play.com",
    "dood.pm",
    "dood.wf",
    "dood.cx",
    "playmogo.com",
    "do0od.com",
]


class DoodStreamExtractor:
    """Extractor for DoodStream / Playmogo video embeds."""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session(impersonate="chrome124")

    @staticmethod
    def can_handle(url: str) -> bool:
        """Check if URL belongs to any DoodStream domain."""
        low = url.lower()
        return any(d in low for d in DOOD_DOMAINS)

    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """Extract Dood video ID from URL."""
        m = re.search(r"/(?:e|d)/([a-zA-Z0-9]+)", url, re.IGNORECASE)
        if m:
            return m.group(1)
        m_q = re.search(r"[?&]v=([a-zA-Z0-9]+)", url, re.IGNORECASE)
        if m_q:
            return m_q.group(1)
        return None

    def extract(self, embed_url: str, referer: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract direct video stream link from DoodStream embed.

        :param embed_url: DoodStream embed URL
        :param referer: Optional referring URL
        :return: Dict containing direct stream URL, poster, and metadata
        """
        url = embed_url.strip()
        video_id = self.extract_video_id(url)
        if not video_id:
            raise ValueError(f"Could not extract DoodStream video ID from URL: {embed_url}")

        # Extract base domain from embed_url
        domain_match = re.search(r"https?://[^/]+", url)
        base_domain = domain_match.group(0) if domain_match else "https://dood.to"

        ref = referer or url
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": ref,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        # Strategy 1: High-Speed Direct HTML + pass_md5 token call
        try:
            page_url = f"{base_domain}/e/{video_id}"
            res = self.session.get(page_url, headers=headers, timeout=12)
            if res.status_code == 200:
                html_text = res.text

                # Extract title and poster
                title_m = re.search(r"<title>(.*?)</title>", html_text, re.IGNORECASE)
                title = title_m.group(1).replace("Watch ", "").strip() if title_m else f"DoodStream {video_id}"

                poster_m = re.search(r'splash\s*:\s*["\']([^"\']+)["\']', html_text)
                poster = poster_m.group(1) if poster_m else None

                # Extract pass_md5 path
                pass_path = None
                p_match = re.search(r"['\"](/pass_md5/[^'\"]+)['\"]", html_text)
                if p_match:
                    pass_path = p_match.group(1)
                else:
                    alt_m = re.search(r"\$\.get\(\s*['\"](/pass_md5/[^'\"]+)['\"]", html_text)
                    if alt_m:
                        pass_path = alt_m.group(1)

                if pass_path:
                    token_url = f"{base_domain}{pass_path}"
                    token_suffix = pass_path.split("/")[-1]

                    token_res = self.session.get(
                        token_url,
                        headers={"Referer": page_url, "User-Agent": headers["User-Agent"]},
                        timeout=10,
                    )
                    if token_res.status_code == 200 and token_res.text:
                        raw_base = token_res.text.strip()
                        # Dood dynamic makePlay() token generation:
                        rand_salt = "".join(random.choices(string.ascii_letters + string.digits, k=10))
                        expiry = int(time.time() * 1000)
                        stream_url = f"{raw_base}{rand_salt}?token={token_suffix}&expiry={expiry}"

                        return {
                            "server": "DoodStream",
                            "video_id": video_id,
                            "title": title,
                            "poster": poster,
                            "master_m3u8": stream_url if ".m3u8" in stream_url else None,
                            "direct_sources": [
                                {
                                    "quality": "default",
                                    "url": stream_url,
                                    "type": "video/mp4" if ".m3u8" not in stream_url else "application/x-mpegURL",
                                }
                            ],
                            "headers": {"Referer": page_url},
                        }
        except Exception as e:
            logger.warning(f"Direct DoodStream pass_md5 failed for {video_id}: {e}. Trying yt-dlp fallback...")

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
                    "server": "DoodStream",
                    "video_id": video_id,
                    "title": info.get("title"),
                    "poster": info.get("thumbnail"),
                    "duration": info.get("duration"),
                    "master_m3u8": master_m3u8,
                    "direct_sources": direct_sources,
                    "headers": {"Referer": url},
                }
        except Exception as e:
            logger.error(f"yt-dlp fallback failed for DoodStream {video_id}: {e}")
            raise RuntimeError(f"Failed to extract DoodStream stream for {video_id}: {e}")
