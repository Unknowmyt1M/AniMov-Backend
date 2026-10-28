"""
MegaPlay / MegaCloud / RapidCloud Stream Extractor.
Extracts direct master HLS .m3u8 stream, tracks, and subtitles from MegaPlay embeds
(megaplay.buzz, megacloud.tv, vidstream.pro, rapid-cloud.co).

Reverse-engineered from MegaPlay player scripts (AES-256-CBC decryption with key seed).
"""

import re
import json
import base64
import logging
from typing import Dict, Any, Optional, List
from curl_cffi import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

logger = logging.getLogger("extractors.megaplay")

MEGAPLAY_DOMAINS = [
    "megaplay.buzz",
    "megacloud.tv",
    "vidstream.pro",
    "rapid-cloud.co",
]

DEFAULT_KEY_SEED = "i?LMTAx0Q6,:}50U"
DEFAULT_IV_SEED = "W0;27ToaUpl_P%'c"


def _seed_to_bytes(seed: str, length: int) -> bytes:
    """Pad or truncate string seed to exactly length bytes with nulls."""
    b = seed.encode("utf-8")
    if len(b) < length:
        return b + b"\x00" * (length - len(b))
    return b[:length]


def decrypt_megaplay_payload(enc_payload: str, key_seed: str = DEFAULT_KEY_SEED, iv_seed: str = DEFAULT_IV_SEED) -> Optional[Dict[str, Any]]:
    """Decrypt MegaPlay's AES-256-CBC ciphertext."""
    if not enc_payload or not isinstance(enc_payload, str):
        return None
    try:
        key = _seed_to_bytes(key_seed, 32)
        iv = _seed_to_bytes(iv_seed, 16)

        padded = enc_payload + "=" * ((4 - len(enc_payload) % 4) % 4)
        raw_ciphertext = base64.urlsafe_b64decode(padded)

        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_raw = unpad(cipher.decrypt(raw_ciphertext), AES.block_size)
        return json.loads(decrypted_raw.decode("utf-8"))
    except Exception as e:
        logger.debug(f"MegaPlay AES decryption failed with primary seed: {e}")
        return None


class MegaPlayExtractor:
    """Extractor for MegaPlay / MegaCloud video embeds."""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session(impersonate="chrome124")

    @staticmethod
    def can_handle(url: str) -> bool:
        """Check if URL belongs to any MegaPlay domain."""
        low = url.lower()
        return any(d in low for d in MEGAPLAY_DOMAINS)

    @staticmethod
    def extract_source_id(url: str, html_text: str = "") -> Optional[str]:
        """Extract data-id / episode ID from HTML or URL."""
        if html_text:
            m_data = re.search(r'data-id\s*=\s*["\']([0-9]+)["\']', html_text)
            if m_data:
                return m_data.group(1)
            m_id = re.search(r'id\s*:\s*["\']?([0-9]+)["\']?', html_text)
            if m_id:
                return m_id.group(1)

        m_path = re.search(r"/(?:stream|embed-2|e-1)/(?:[a-zA-Z0-9_-]+/)?([0-9]+)", url)
        if m_path:
            return m_path.group(1)
        m_q = re.search(r"[?&]id=([0-9]+)", url)
        if m_q:
            return m_q.group(1)
        return None

    def extract(self, embed_url: str, referer: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract direct HLS .m3u8 link and subtitles from MegaPlay embed.

        :param embed_url: MegaPlay embed URL
        :param referer: Optional referring URL
        :return: Dict containing master_m3u8, tracks, etc.
        """
        url = embed_url.strip()
        domain_match = re.search(r"https?://[^/]+", url)
        base_domain = domain_match.group(0) if domain_match else "https://megaplay.buzz"

        ref = referer or "https://anikoto.cz/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": ref,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        # Strategy 1: Fetch embed page -> parse data-id -> call /stream/getSourcesNew
        try:
            res = self.session.get(url, headers=headers, timeout=12)
            if res.status_code == 200:
                html_text = res.text
                source_id = self.extract_source_id(url, html_text)

                if source_id:
                    ajax_url = f"{base_domain}/stream/getSourcesNew?id={source_id}"
                    ajax_headers = {
                        **headers,
                        "Referer": url,
                        "X-Requested-With": "XMLHttpRequest",
                        "Accept": "application/json, text/javascript, */*; q=0.01",
                    }
                    sources_res = self.session.get(ajax_url, headers=ajax_headers, timeout=10)
                    if sources_res.status_code == 200:
                        data = sources_res.json()
                        tracks = data.get("tracks", [])
                        master_m3u8 = None

                        # Check if sources are cleartext
                        sources_list = data.get("sources")
                        if isinstance(sources_list, list) and sources_list:
                            master_m3u8 = sources_list[0].get("file")
                        elif isinstance(sources_list, str):
                            master_m3u8 = sources_list

                        # Check if encrypted with AES-256
                        enc_payload = data.get("enc") or data.get("sources")
                        if not master_m3u8 and isinstance(enc_payload, str):
                            decrypted = decrypt_megaplay_payload(enc_payload)
                            if decrypted:
                                master_m3u8 = decrypted.get("file") or decrypted.get("sources")
                                if isinstance(master_m3u8, list) and master_m3u8:
                                    master_m3u8 = master_m3u8[0].get("file")

                        if master_m3u8:
                            subtitles = [
                                {
                                    "label": t.get("label", "Sub"),
                                    "url": t.get("file"),
                                    "kind": t.get("kind", "captions"),
                                }
                                for t in tracks
                                if t.get("file")
                            ]
                            return {
                                "server": "MegaPlay",
                                "source_id": source_id,
                                "master_m3u8": master_m3u8,
                                "subtitles": subtitles,
                                "headers": {"Referer": url},
                            }
        except Exception as e:
            logger.warning(f"Direct MegaPlay API failed for {url}: {e}. Trying yt-dlp fallback...")

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
                    "server": "MegaPlay",
                    "title": info.get("title"),
                    "poster": info.get("thumbnail"),
                    "duration": info.get("duration"),
                    "master_m3u8": master_m3u8,
                    "direct_sources": direct_sources,
                    "headers": {"Referer": url},
                }
        except Exception as e:
            logger.error(f"yt-dlp fallback failed for MegaPlay ({url}): {e}")
            raise RuntimeError(f"Failed to extract MegaPlay stream for {url}: {e}")
