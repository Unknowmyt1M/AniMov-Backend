"""
Abyss Player & DubPlayer Extractor.
Extracts multi-audio streams from WatchAnimeWorld's dub-player and player.abyssplayer.com.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional
from curl_cffi import requests

logger = logging.getLogger("extractors.abyss")


class AbyssExtractor:
    """Extractor for /dub-player/ and player.abyssplayer.com streams."""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session(impersonate="chrome124")

    @staticmethod
    def can_handle(url: str) -> bool:
        """Check if URL is an Abyss or DubPlayer embed."""
        low = url.lower()
        return "abyssplayer.com" in low or "dub-player" in low

    def extract(self, embed_url: str, referer: Optional[str] = None) -> Dict[str, Any]:
        """
        Unified extraction method for Abyss player or DubPlayer embed.

        :param embed_url: DubPlayer or Abyss player URL
        :param referer: Optional referring URL
        :return: Dict containing stream sources and metadata
        """
        ref = referer or "https://watchanimeworld.one/"
        if "dub-player" in embed_url.lower():
            dub_info = self.extract_from_dub_player(embed_url, referer=ref)
            streams_by_lang = dub_info.get("streams_by_lang", {})
            direct_sources = []
            # Resolve the first available language's stream (prefer 'hin' if available)
            target_lang = "hin" if "hin" in streams_by_lang else (next(iter(streams_by_lang)) if streams_by_lang else None)
            if target_lang and streams_by_lang.get(target_lang):
                try:
                    direct_sources = self.extract_direct_sources(streams_by_lang[target_lang])
                except Exception as e:
                    logger.warning(f"Could not resolve direct sources for {target_lang}: {e}")

            return {
                "server": "DubPlayer (Abyss)",
                "title": dub_info.get("title"),
                "season": dub_info.get("season"),
                "episode": dub_info.get("episode"),
                "languages": dub_info.get("languages", []),
                "streams_by_lang": streams_by_lang,
                "selected_lang": target_lang,
                "direct_sources": direct_sources,
                "headers": {"Referer": ref},
            }
        else:
            sources = self.extract_direct_sources(embed_url)
            return {
                "server": "Abyss",
                "embed_url": embed_url,
                "direct_sources": sources,
                "headers": {"Referer": ref},
            }

    def extract_from_dub_player(self, dub_player_url: str, referer: str = "https://watchanimeworld.one/") -> Dict[str, Any]:
        """
        Extract multi-language audio mappings from /dub-player/ page.

        :param dub_player_url: URL like https://watchanimeworld.one/dub-player/t/8545/
        :param referer: Page referer URL
        :return: Dict containing title, languages available, and stream mappings.
        """
        res = self.session.get(
            dub_player_url,
            headers={
                "Referer": referer,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            },
            timeout=15,
        )
        if res.status_code != 200:
            raise RuntimeError(f"DubPlayer returned HTTP {res.status_code}")

        # Extract CONFIG JSON
        config_match = re.search(r"var\s+CONFIG\s*=\s*(\{.*?\});", res.text, re.DOTALL)
        if not config_match:
            raise ValueError("Could not find CONFIG object in DubPlayer page")

        config = json.loads(config_match.group(1))
        prefix = config.get("prefix", "https://player.abyssplayer.com/")
        ready_map = config.get("ready", {})

        streams_by_lang: Dict[str, str] = {}
        for lang_code, stream_id in ready_map.items():
            full_url = f"{prefix.rstrip('/')}/{stream_id}"
            streams_by_lang[lang_code] = full_url

        return {
            "server": "DubPlayer (Abyss)",
            "title": config.get("title"),
            "season": config.get("season"),
            "episode": config.get("episode"),
            "languages": list(streams_by_lang.keys()),
            "streams_by_lang": streams_by_lang,
        }

    def extract_direct_sources(self, abyss_player_url: str) -> List[Dict[str, Any]]:
        """
        Resolve player.abyssplayer.com/{id} into direct playable video streams (360p, 720p, 1080p).

        :param abyss_player_url: URL like https://player.abyssplayer.com/JPRG69Zz-
        :return: List of stream sources with url, resolution, codec, size
        """
        res = self.session.get(
            abyss_player_url,
            headers={
                "Referer": "https://watchanimeworld.one/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            },
            timeout=15,
        )
        if res.status_code != 200:
            raise RuntimeError(f"Abyss player returned HTTP {res.status_code}")

        # Extract datas string
        match = re.search(r'const\s+datas\s*=\s*"([^"]*)"', res.text)
        if not match:
            raise ValueError("Could not find encrypted datas payload in Abyss page")

        datas = match.group(1)

        # Call decryptor API
        dec_res = self.session.post(
            "https://enc-dec.app/api/dec-abyss",
            json={"text": datas},
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
            timeout=15,
        )
        if dec_res.status_code != 200:
            raise RuntimeError(f"Decryption API returned HTTP {dec_res.status_code}")

        dec_json = dec_res.json()
        result = dec_json.get("result", {})
        sources = result.get("sources", [])

        return [
            {
                "url": s.get("url"),
                "quality": s.get("type"),
                "size_bytes": s.get("size"),
                "codec": s.get("codec"),
            }
            for s in sources
            if s.get("url")
        ]
