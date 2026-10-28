"""
Zephyrix (MultiCloud / Zephyrflick) Stream Extractor.
Extracts direct master HLS .m3u8 stream and captions from play.zephyrix.org embeds.
"""

import re
import logging
from typing import Dict, Any, Optional
from curl_cffi import requests

from .unpacker import unpack_js, is_packed

logger = logging.getLogger("extractors.zephyrix")


class ZephyrixExtractor:
    """Extractor for play.zephyrix.org / MultiCloud video embeds."""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session(impersonate="chrome124")

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video hash / ID from embed URL."""
        match = re.search(r"/(?:video|v)/([a-zA-Z0-9_-]+)", url)
        if match:
            return match.group(1)
        # fallback to last segment
        parts = url.rstrip("/").split("/")
        return parts[-1] if parts else None

    def extract(self, embed_url: str, referer: str = "https://watchanimeworld.one/") -> Dict[str, Any]:
        """
        Extract direct HLS .m3u8 link and metadata from a Zephyrix embed.

        :param embed_url: URL like https://play.zephyrix.org/video/{video_id}
        :param referer: Page referer URL
        :return: Dict containing 'master_m3u8', 'video_image', 'subtitles', etc.
        """
        video_id = self._extract_video_id(embed_url)
        if not video_id:
            raise ValueError(f"Could not extract video ID from URL: {embed_url}")

        domain_match = re.search(r"https?://[^/]+", embed_url)
        base_domain = domain_match.group(0) if domain_match else "https://play.zephyrix.org"

        # 1. Fetch embed page to extract captions and check packed JS
        captions = []
        try:
            page_res = self.session.get(
                embed_url,
                headers={
                    "Referer": referer,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                },
                timeout=15,
            )
            if page_res.status_code == 200:
                html = page_res.text
                if is_packed(html):
                    unpacked = unpack_js(html)
                    if unpacked:
                        # Extract tracks if present
                        track_matches = re.findall(
                            r'\{"kind":"captions","file":"([^"]+)","label":"([^"]+)"',
                            unpacked,
                        )
                        for file_url, label in track_matches:
                            clean_file = file_url.replace(r"\/", "/")
                            captions.append({"label": label, "url": clean_file})
        except Exception as e:
            logger.warning(f"Error inspecting Zephyrix embed page: {e}")

        # 2. Call getVideo backend API
        post_url = f"{base_domain}/player/index.php?data={video_id}&do=getVideo"
        headers = {
            "Referer": embed_url,
            "Origin": base_domain,
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        }
        data = {
            "hash": video_id,
            "r": referer,
        }

        res = self.session.post(post_url, data=data, headers=headers, timeout=15)
        if res.status_code != 200:
            raise RuntimeError(f"Zephyrix API returned HTTP {res.status_code}")

        res_json = res.json()
        master_m3u8 = res_json.get("securedLink") or res_json.get("videoSource")

        return {
            "server": "MultiCloud (Zephyrix)",
            "video_id": video_id,
            "master_m3u8": master_m3u8,
            "poster": res_json.get("videoImage"),
            "captions": captions,
            "is_hls": res_json.get("hls", True),
        }
