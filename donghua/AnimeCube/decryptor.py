"""
AnimeCube Stream Resolver & AES-GCM Decryptor.

Reverse-engineered from AnimeCube's Next.js client-side player architecture:
1. Version Registry:
   - Fetches /api/anime-sources-versions with random X-Obf hex header.
   - Extracts X-Registry-ETag from response headers.
   - Decrypts base64 AES-GCM ciphertext using SHA-256(X-Obf + "|" + ETag) and 12-byte IV.
   - Maps (slug, primaryTabId, seasonId) to active version string.

2. Episode Video Sources:
   - Queries /api/anime/{slug}/episode/{episodeId}/sources?v={version}&primaryTabId={primaryTabId}&seasonId={seasonId}
   - Supplies fresh random X-Obf hex header.
   - Decrypts base64 AES-GCM ciphertext using SHA-256(X-Obf + "|" + version) and 12-byte IV.
   - Extracts real video streaming providers (Dailymotion, Rumble, YouTube, etc.) with videoId, privateId, quality.
"""
import time
import json
import base64
import hashlib
import secrets
from typing import Dict, Any, List, Optional
from curl_cffi import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import PRIMARY_DOMAIN
from .models import StreamServer


class AnimeCubeStreamResolver:
    def __init__(self, cache_ttl_seconds: float = 300.0):
        self._registry_cache: Optional[Dict[str, Any]] = None
        self._registry_etag: Optional[str] = None
        self._registry_timestamp: float = 0.0
        self.cache_ttl = cache_ttl_seconds

    def _decrypt_payload(self, b64_ciphertext: str, seed_str: str) -> Dict[str, Any]:
        """
        Decrypts an AnimeCube AES-GCM encrypted payload.
        First 12 bytes = IV, remaining bytes = ciphertext + 16-byte authentication tag.
        Key = SHA-256(seed_str).
        """
        key = hashlib.sha256(seed_str.encode("utf-8")).digest()
        raw = base64.b64decode(b64_ciphertext)
        if len(raw) < 28:
            raise ValueError(f"Payload too short for AES-GCM (len={len(raw)})")
        iv = raw[:12]
        ciphertext_and_tag = raw[12:]
        aesgcm = AESGCM(key)
        decrypted_bytes = aesgcm.decrypt(iv, ciphertext_and_tag, None)
        return json.loads(decrypted_bytes.decode("utf-8"))

    def get_sources_registry(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Fetches and decrypts /api/anime-sources-versions to get the version registry.
        Caches for TTL seconds unless force_refresh is True.
        """
        now = time.time()
        if not force_refresh and self._registry_cache and (now - self._registry_timestamp < self.cache_ttl):
            return self._registry_cache

        x_obf = secrets.token_hex(16)
        headers = {
            "Accept": "application/json",
            "X-Obf": x_obf,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": f"{PRIMARY_DOMAIN}/"
        }
        if self._registry_etag and not force_refresh:
            headers["If-None-Match"] = self._registry_etag

        url = f"{PRIMARY_DOMAIN}/api/anime-sources-versions"
        try:
            resp = requests.get(url, headers=headers, impersonate="chrome124", timeout=15)
            if resp.status_code == 304 and self._registry_cache:
                self._registry_timestamp = now
                return self._registry_cache

            if resp.status_code != 200:
                return self._registry_cache or {"bySeason": {}}

            etag = resp.headers.get("x-registry-etag") or resp.headers.get("X-Registry-ETag") or resp.headers.get("etag") or ""
            data = resp.json()

            if isinstance(data, dict) and "d" in data:
                seed = f"{x_obf}|{etag}"
                registry = self._decrypt_payload(data["d"], seed)
                self._registry_cache = registry
                self._registry_etag = etag
                self._registry_timestamp = now
                return registry
            elif isinstance(data, dict) and "bySeason" in data:
                self._registry_cache = data
                self._registry_etag = etag
                self._registry_timestamp = now
                return data

        except Exception:
            pass

        return self._registry_cache or {"bySeason": {}}

    def get_version_for_episode(
        self,
        slug: str,
        primary_tab_id: Optional[str] = None,
        season_id: Optional[str] = None,
        force_refresh: bool = False
    ) -> Optional[str]:
        """
        Resolves the active version string `v` for a specific anime series, tab, and season.
        """
        registry = self.get_sources_registry(force_refresh=force_refresh)
        by_season = registry.get("bySeason", {})
        series_data = by_season.get(slug)

        if not series_data and not force_refresh:
            registry = self.get_sources_registry(force_refresh=True)
            by_season = registry.get("bySeason", {})
            series_data = by_season.get(slug)

        if not series_data:
            return None

        # 1. Exact match for primary_tab_id and season_id
        if primary_tab_id and season_id:
            tab_data = series_data.get(primary_tab_id)
            if isinstance(tab_data, dict) and season_id in tab_data:
                return tab_data[season_id]

        # 2. Match season_id in any tab
        if season_id:
            for tab_id, seasons in series_data.items():
                if isinstance(seasons, dict) and season_id in seasons:
                    return seasons[season_id]

        # 3. Match primary_tab_id first season
        if primary_tab_id and primary_tab_id in series_data:
            tab_data = series_data[primary_tab_id]
            if isinstance(tab_data, dict) and tab_data:
                return next(iter(tab_data.values()))

        # 4. First available season in first tab
        for tab_id, seasons in series_data.items():
            if isinstance(seasons, dict) and seasons:
                return next(iter(seasons.values()))

        return None

    def resolve_episode_sources(
        self,
        slug: str,
        episode_id: str,
        primary_tab_id: str = "primary-1",
        season_id: str = "tab-1"
    ) -> List[StreamServer]:
        """
        Resolves and decrypts the streaming servers and direct video sources for an episode.
        Returns a list of StreamServer objects with decoded embed URLs and metadata.
        """
        version = self.get_version_for_episode(slug, primary_tab_id, season_id)
        servers: List[StreamServer] = []

        if version:
            servers = self._fetch_and_decrypt_sources(
                slug=slug,
                episode_id=episode_id,
                version=version,
                primary_tab_id=primary_tab_id,
                season_id=season_id
            )

            # If failed (e.g. 404/410 version rotated), retry once with force_refresh
            if not servers:
                new_version = self.get_version_for_episode(slug, primary_tab_id, season_id, force_refresh=True)
                if new_version and new_version != version:
                    servers = self._fetch_and_decrypt_sources(
                        slug=slug,
                        episode_id=episode_id,
                        version=new_version,
                        primary_tab_id=primary_tab_id,
                        season_id=season_id
                    )

        # Always include the web player as a reliable fallback
        web_player_url = f"{PRIMARY_DOMAIN}/anime/{slug}?season={season_id}&episode={episode_id}"
        servers.append(
            StreamServer(
                server_name="AnimeCube Web Player",
                provider="animecube",
                embed_url=web_player_url,
                quality="1080p / 4K",
                languages=["Multi-Sub", "English"],
                extra_data={"web_player": True}
            )
        )

        return servers

    def _fetch_and_decrypt_sources(
        self,
        slug: str,
        episode_id: str,
        version: str,
        primary_tab_id: str,
        season_id: str
    ) -> List[StreamServer]:
        """
        Calls /api/anime/{slug}/episode/{episode_id}/sources and decrypts the response.
        """
        x_obf = secrets.token_hex(16)
        headers = {
            "Accept": "application/json",
            "X-Obf": x_obf,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": f"{PRIMARY_DOMAIN}/anime/{slug}"
        }

        url = f"{PRIMARY_DOMAIN}/api/anime/{slug}/episode/{episode_id}/sources?v={version}&primaryTabId={primary_tab_id}&seasonId={season_id}"

        try:
            resp = requests.get(url, headers=headers, impersonate="chrome124", timeout=15)
            if resp.status_code != 200:
                return []

            data = resp.json()
            if not isinstance(data, dict) or "d" not in data:
                return []

            seed = f"{x_obf}|{version}"
            decrypted = self._decrypt_payload(data["d"], seed)
            raw_sources = decrypted.get("sources", [])
            servers: List[StreamServer] = []

            for src in raw_sources:
                platform = src.get("platform", "").lower()
                video_id = src.get("videoId", "")
                quality = src.get("quality", "1080p")
                private_id = src.get("privateId")
                good_sub = src.get("goodSub", False)

                embed_url = ""
                server_name = ""

                if platform == "dailymotion":
                    embed_url = f"https://geo.dailymotion.com/player.html?video={video_id}"
                    server_name = f"Dailymotion [{quality}]"
                elif platform == "rumble":
                    embed_url = f"https://rumble.com/embed/{video_id}/"
                    server_name = f"Rumble [{quality}]"
                elif platform == "youtube":
                    embed_url = f"https://www.youtube.com/embed/{video_id}"
                    server_name = f"YouTube [{quality}]"
                else:
                    embed_url = f"{PRIMARY_DOMAIN}/anime/{slug}?season={season_id}&episode={episode_id}"
                    server_name = f"Provider ({platform}) [{quality}]"

                servers.append(
                    StreamServer(
                        server_name=server_name,
                        provider=platform or "unknown",
                        embed_url=embed_url,
                        quality=quality,
                        languages=["Multi-Sub", "English"],
                        platform=platform,
                        video_id=video_id,
                        private_id=private_id,
                        good_sub=good_sub,
                        extra_data=src
                    )
                )

            return servers

        except Exception:
            return []
