"""Stream Resolver & Decryptor for Live HLS Master Playlists."""

import logging
import time
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import httpx
from bs4 import BeautifulSoup
from anime.animesuge.decryptor import decrypt_megaplay_sources

logger = logging.getLogger("animov.resolver")

# Cache format: cache_key -> (timestamp, data_dict, is_complete_bool)
STREAM_CACHE: Dict[str, Tuple[float, Dict[str, Any], bool]] = {}

class StreamResolver:
    """Resolves and decrypts live HLS master.m3u8 playlists from upstream anime embeds."""

    @staticmethod
    async def _resolve_background_mirrors(
        slug: str,
        episode_number: int,
        lang: str,
        cache_key: str,
        embeds: list,
    ):
        """Asynchronously resolve secondary provider mirrors and decrypted embeds in the background."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Referer": "https://anikage.cc/",
        }

        async with httpx.AsyncClient(headers=headers, timeout=6.0, follow_redirects=True) as client:
            async def resolve_provider(prov_name: str, label: str):
                try:
                    url = f"https://anikage.cc/api/media/anime/{slug}/episodes/{episode_number}/sources?lang={lang}&provider={prov_name}&server={prov_name}"
                    res = await client.get(url, timeout=4.0)
                    if res.status_code == 200:
                        data = res.json()
                        for s in data.get("sources", []):
                            token = s.get("url", "")
                            if token.startswith("AccUU"):
                                return {
                                    "providerId": prov_name,
                                    "serverName": label,
                                    "quality": "Multi-Quality",
                                    "url": f"https://og.bakayaro.live/m3u8/{token}",
                                    "referer": "https://anikage.cc/",
                                    "isM3u8": True,
                                    "streamType": lang,
                                }
                except Exception as ex:
                    logger.debug(f"Background provider {prov_name} error: {ex}")
                return None

            async def resolve_embed(emb: dict):
                try:
                    emb_url = emb.get("url", "")
                    srv_name = emb.get("server", "HD-1")
                    r = await client.get(emb_url, headers={"Referer": "https://anikage.cc/"}, timeout=4.0)
                    soup = BeautifulSoup(r.text, "html.parser")
                    player = soup.select_one("#megaplay-player")
                    if player:
                        data_id = player.get("data-id")
                        sources_url = "https://megaplay.buzz/stream/getSourcesNew"
                        s_res = await client.get(
                            sources_url,
                            params={"id": data_id},
                            headers={"Referer": emb_url, "X-Requested-With": "XMLHttpRequest"},
                            timeout=4.0,
                        )
                        if s_res.status_code == 200:
                            enc_payload = s_res.json().get("enc", "")
                            if enc_payload:
                                decrypted = decrypt_megaplay_sources(enc_payload)
                                if decrypted and decrypted.get("file"):
                                    return {
                                        "providerId": "megaplay",
                                        "serverName": f"MegaPlay - {srv_name}",
                                        "quality": "1080p FHD",
                                        "url": decrypted.get("file"),
                                        "referer": "https://megaplay.buzz/",
                                        "isM3u8": True,
                                        "streamType": lang,
                                    }
                except Exception as ex:
                    logger.debug(f"Background embed error: {ex}")
                return None

            tasks = [
                resolve_provider("ken", "HD-2 Multi-Quality (Server Ken)"),
                resolve_provider("wave", "HD-3 Multi-Quality (Server Wave)"),
            ]
            for emb in embeds[:2]:
                tasks.append(resolve_embed(emb))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            if cache_key in STREAM_CACHE:
                ts, cached_res, _ = STREAM_CACHE[cache_key]
                existing_urls = {s.get("url") for s in cached_res.get("sources", [])}
                for item in results:
                    if isinstance(item, dict) and item.get("url"):
                        if item["url"] not in existing_urls:
                            cached_res["sources"].append(item)
                            existing_urls.add(item["url"])
                cached_res["hasMore"] = False
                STREAM_CACHE[cache_key] = (ts, cached_res, True)
                logger.info(f"Background loaded {len(cached_res['sources'])} servers for {cache_key}")

    @staticmethod
    async def resolve_episode_streams(slug: str, episode_number: int, lang: str = "sub", wait_for_all: bool = False) -> Dict[str, Any]:
        """Fetch sources from Anikage, extract multi-quality adaptive streams and decrypt live master.m3u8 playlists."""
        cache_key = f"{slug}:{episode_number}:{lang}"
        now = time.time()
        if cache_key in STREAM_CACHE:
            ts, cached_res, is_complete = STREAM_CACHE[cache_key]
            if now - ts < 900:  # 15 minutes TTL
                if is_complete or not wait_for_all:
                    logger.info(f"Serving stream for {cache_key} instantly from cache (complete={is_complete})")
                    return cached_res

        url = f"https://anikage.cc/api/media/anime/{slug}/episodes/{episode_number}/sources"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Referer": "https://anikage.cc/",
        }

        async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
            try:
                res = await client.get(url, params={"lang": lang, "provider": "koto", "server": "koto"})
                if res.status_code != 200:
                    logger.warning(f"Anikage sources returned status {res.status_code}")
                    return {"sources": [], "subtitles": []}

                data = res.json()
            except Exception as e:
                logger.error(f"Error querying Anikage sources: {e}")
                return {"sources": [], "subtitles": []}

            intro = data.get("intro")
            outro = data.get("outro")
            sources_raw = data.get("sources", [])
            embeds = data.get("embeds", [])
            subtitles_raw = data.get("subtitles", [])

            resolved_sources = []

            # 1. Direct Multi-Quality Adaptive HLS Stream (from og.bakayaro.live with 1080p, 720p, 480p)
            for src in sources_raw:
                token = src.get("url", "")
                if token.startswith("AccUU"):
                    m3u8_url = f"https://og.bakayaro.live/m3u8/{token}"
                    resolved_sources.append({
                        "providerId": "bakayaro",
                        "serverName": "HD-1 Multi-Quality (1080p/720p/480p)",
                        "quality": "Multi-Quality",
                        "url": m3u8_url,
                        "referer": "https://anikage.cc/",
                        "isM3u8": True,
                        "streamType": lang,
                    })

            # Subtitles & Thumbnails formatting
            subtitles = []
            thumbnails = None
            for s in subtitles_raw:
                file_url = s.get("file", "")
                if file_url.startswith("AccUU"):
                    file_url = f"https://og.bakayaro.live/m3u8/{file_url}"

                kind = s.get("kind", "captions")
                if kind == "thumbnails":
                    thumbnails = file_url
                    continue

                if file_url.startswith("http"):
                    label = s.get("label", "English")
                    subtitles.append({
                        "label": label,
                        "file": file_url,
                        "lang": label.lower()[:2] if label else "en",
                        "default": bool(s.get("default", False)),
                        "kind": kind,
                    })

            initial_res = {
                "slug": slug,
                "episode": episode_number,
                "lang": lang,
                "intro": intro,
                "outro": outro,
                "sources": list(resolved_sources),
                "subtitles": subtitles,
                "thumbnails": thumbnails,
                "hasMore": True,
            }

            # Cache the fast initial result immediately
            STREAM_CACHE[cache_key] = (now, initial_res, False)

            # Trigger background task for all other mirrors
            bg_coro = StreamResolver._resolve_background_mirrors(slug, episode_number, lang, cache_key, embeds)
            if wait_for_all:
                await bg_coro
                return STREAM_CACHE[cache_key][1]
            else:
                asyncio.create_task(bg_coro)
                return initial_res
