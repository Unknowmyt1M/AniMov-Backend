"""Core Scraper and API Client for Anikage Anime."""

import logging
import time
from typing import List, Optional, Dict, Any, Tuple

from .http_client import AnikageHttpClient
from .config import API_BASE_URL
from .models import (
    AnikageSearchResult,
    AnikageDetail,
    AnikageEpisode,
    AnikageStreamSource,
    AnikageSubtitle,
    AnikageRelation,
    AnikageRecommendation,
)

logger = logging.getLogger("anikage.scraper")


class AnikageScraper:
    """Scraper implementation for Anikage Anime (REST API)."""

    def __init__(self, http_client: Optional[AnikageHttpClient] = None):
        self.http = http_client or AnikageHttpClient()
        self._detail_cache: Dict[str, Tuple[float, AnikageDetail]] = {}

    def _parse_search_item(self, item: Dict[str, Any]) -> AnikageSearchResult:
        slug = item.get("slug", "")
        title_obj = item.get("title", {})
        romaji = title_obj.get("romaji", "")
        english = title_obj.get("english")
        native = title_obj.get("native")
        display = english or romaji or slug

        cover = item.get("coverImage", {})
        poster = cover.get("large") or cover.get("medium") if isinstance(cover, dict) else None

        format_val = item.get("format", "TV")
        status = item.get("status")
        score = item.get("averageScore")
        if score is not None:
            try:
                score = round(float(score) / 10.0, 1) if float(score) > 10 else float(score)
            except (ValueError, TypeError):
                pass

        genres = item.get("genres", [])

        return AnikageSearchResult(
            slug=slug,
            romaji=romaji,
            english=english,
            native=native,
            display_title=display,
            poster=poster,
            format=format_val,
            status=status,
            score=score,
            genres=genres,
        )

    def search(self, query: str, page: int = 1, limit: int = 20) -> List[AnikageSearchResult]:
        """Search anime by keyword."""
        cleaned_query = query.strip() if query else ""
        if not cleaned_query:
            return []

        url = f"{API_BASE_URL}/search"
        # Fetch up to required page boundary to support pagination cleanly
        fetch_limit = max(limit * page, limit)
        params = {
            "q": cleaned_query,
            "limit": fetch_limit,
        }
        resp = self.http.get(url, params=params)
        try:
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"AniKage returned malformed JSON response: {e}")

        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected response format from AniKage: {type(data)}")

        items = data.get("data", [])
        if not isinstance(items, list):
            items = []

        # Apply deterministic page slicing
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paged_items = items[start_idx:end_idx]

        return [self._parse_search_item(i) for i in paged_items if isinstance(i, dict)]

    def get_catalog(
        self,
        sort: str = "trending",  # 'trending', 'popularity', 'updated'
        format_filter: Optional[str] = None,  # 'MOVIE', 'OVA', 'TV'
        page: int = 1,
        limit: int = 20,
    ) -> List[AnikageSearchResult]:
        """Browse anime catalog sorted by trending, popularity, or updates."""
        url = f"{API_BASE_URL}/browse"
        params = {
            "sort": sort,
            "page": page,
            "limit": limit,
            "adult": "true",
        }
        if format_filter:
            params["format"] = format_filter
        if sort == "updated":
            params["status"] = "RELEASING"

        resp = self.http.get(url, params=params)
        data = resp.json()

        items = data.get("data", [])
        return [self._parse_search_item(i) for i in items]

    def get_detail(self, slug: str, include_episodes: bool = True) -> AnikageDetail:
        """Fetch anime details and episode catalog."""
        cache_key = f"{slug}:{include_episodes}"
        now = time.time()
        if cache_key in self._detail_cache:
            ts, cached_detail = self._detail_cache[cache_key]
            if now - ts < 1800:  # 30 mins TTL
                return cached_detail

        url = f"{API_BASE_URL}/{slug}"
        try:
            resp = self.http.get(url)
            data = resp.json()
        except RuntimeError as e:
            if "HTTP 404" in str(e):
                logger.debug(f"Anikage anime '{slug}' not found: {e}")
                return None
            raise

        anime = data.get("anime", {})
        title_obj = anime.get("title", {})
        romaji = title_obj.get("romaji", "")
        english = title_obj.get("english")
        native = title_obj.get("native")
        display = english or romaji or slug

        cover = anime.get("coverImage", {})
        poster = cover.get("large") or cover.get("medium") if isinstance(cover, dict) else None
        banner = anime.get("bannerImage")

        synopsis = anime.get("description")
        genres = anime.get("genres", [])
        format_val = anime.get("type") or anime.get("format")
        status = anime.get("status")
        year = anime.get("year") or anime.get("seasonYear")

        score = anime.get("score") or anime.get("averageScore")
        if score is not None:
            try:
                score = round(float(score) / 10.0, 1) if float(score) > 10 else float(score)
            except (ValueError, TypeError):
                pass

        total_episodes = anime.get("totalEpisodes") or 0

        episodes: List[AnikageEpisode] = []
        if include_episodes:
            try:
                episodes = self.get_episodes(slug)
                if not total_episodes:
                    total_episodes = len(episodes)
            except Exception as e:
                logger.warning(f"Failed to fetch episodes for {slug}: {e}")

        detail = AnikageDetail(
            slug=slug,
            romaji=romaji,
            english=english,
            native=native,
            display_title=display,
            poster=poster,
            banner=banner,
            synopsis=synopsis,
            genres=genres,
            format=format_val,
            status=status,
            year=year,
            score=score,
            total_episodes=total_episodes,
            episodes=episodes,
        )
        self._detail_cache[cache_key] = (now, detail)
        return detail

    def get_episodes(self, slug: str) -> List[AnikageEpisode]:
        """Fetch all available episodes for an anime."""
        url = f"{API_BASE_URL}/{slug}/episodes"
        resp = self.http.get(url)
        data = resp.json()

        episodes: List[AnikageEpisode] = []
        if isinstance(data, list):
            raw_list = data
        elif isinstance(data, dict):
            raw_list = data.get("data", [])
        else:
            raw_list = []

        for ep in raw_list:
            ep_id = ep.get("id", "")
            num = ep.get("number", 1)
            title = ep.get("title")
            season = ep.get("seasonNumber", 1)
            air_date = ep.get("airDate")
            rating = ep.get("rating")
            img = ep.get("image")
            desc = ep.get("description")

            episodes.append(
                AnikageEpisode(
                    id=ep_id,
                    slug=slug,
                    number=num,
                    title=title,
                    season_number=season,
                    air_date=air_date,
                    rating=rating,
                    thumbnail=img,
                    description=desc,
                )
            )
        return episodes

    def get_servers(self, slug: str, episode_number: int, lang: str = "sub") -> List[str]:
        """Fetch list of available server/provider IDs for an episode."""
        url = f"{API_BASE_URL}/{slug}/episodes/{episode_number}/servers"
        resp = self.http.get(url, params={"lang": lang})
        data = resp.json()
        servers = data.get("servers", [])
        return [s.get("id") for s in servers if s.get("id")]

    def get_stream_sources(
        self,
        slug: str,
        episode_number: int,
        lang: str = "sub",
        provider: Optional[str] = None,
    ) -> List[AnikageStreamSource]:
        """Fetch streaming video URLs and m3u8 playlists for an episode."""
        if not provider:
            available = self.get_servers(slug, episode_number, lang=lang)
            provider_list = available if available else ["koto", "pam", "nero", "ken", "megg"]
        else:
            provider_list = [provider]

        all_sources: List[AnikageStreamSource] = []

        for p in provider_list:
            url = f"{API_BASE_URL}/{slug}/episodes/{episode_number}/sources"
            try:
                resp = self.http.get(url, params={"lang": lang, "provider": p})
                data = resp.json()
                for src in data.get("sources", []):
                    raw_url = src.get("url", "")
                    quality = src.get("quality") or src.get("label") or "auto"
                    is_m3u8 = bool(src.get("isM3U8", False))

                    all_sources.append(
                        AnikageStreamSource(
                            provider_id=p,
                            quality=quality,
                            url=raw_url,
                            is_m3u8=is_m3u8,
                            stream_type=lang,
                        )
                    )
            except Exception as e:
                logger.debug(f"Failed to fetch sources from {p}: {e}")

        return all_sources

    def close(self):
        self.http.close()
