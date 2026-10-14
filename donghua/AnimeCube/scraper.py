"""
High-level scraper engine for AnimeCube.
Handles Next.js App Router (RSC) extraction, catalog crawling, AES-GCM stream resolution, and database persistence.
"""
import re
from typing import List, Optional
from pathlib import Path

from .config import PRIMARY_DOMAIN, CATALOG_URL
from .http_client import HttpClient
from .models import SeriesDetail, EpisodeDetail, SearchResult, EpisodeSummary, StreamServer
from .rsc_parser import RscParser
from .decryptor import AnimeCubeStreamResolver
from .storage import Storage


class AnimeCubeScraper:
    def __init__(self, cache_enabled: bool = True):
        self.http = HttpClient(cache_enabled=cache_enabled)
        self.storage = Storage()
        self.resolver = AnimeCubeStreamResolver()

    def _normalize_series_url(self, slug_or_url: str) -> str:
        if slug_or_url.startswith("http://") or slug_or_url.startswith("https://"):
            return slug_or_url.split("?")[0]
        clean_slug = slug_or_url.strip("/ ")
        return f"{PRIMARY_DOMAIN}/anime/{clean_slug}"

    def _extract_slug(self, slug_or_url: str) -> str:
        clean = slug_or_url.split("?")[0].strip("/ ")
        if "/anime/" in clean:
            return clean.split("/anime/")[-1]
        return clean

    def list_catalog(self) -> List[SearchResult]:
        """
        Retrieves all series available in AnimeCube's homepage/catalog.
        """
        html_content = self.http.get(CATALOG_URL)
        return RscParser.parse_catalog_from_homepage(html_content)

    def search(self, query: str) -> List[SearchResult]:
        """
        Searches AnimeCube's catalog by matching title or slug with the query.
        """
        catalog = self.list_catalog()
        q_low = query.lower().strip()
        matched = []

        for item in catalog:
            if q_low in item.title.lower() or q_low in item.slug.lower():
                matched.append(item)

        return matched

    def get_series_detail(self, slug_or_url: str) -> SeriesDetail:
        """
        Fetches series metadata and full episode list from Next.js RSC payload.
        """
        url = self._normalize_series_url(slug_or_url)
        slug = self._extract_slug(slug_or_url)

        html_content = self.http.get(url)
        series_detail = RscParser.parse_series_detail(html_content, fallback_slug=slug)

        self.storage.save_series(series_detail)
        return series_detail

    def get_episode_detail(self, slug_or_url: str, episode_id_or_num: str) -> EpisodeDetail:
        """
        Extracts playback and stream server details for a specific episode,
        decrypting real video sources (Dailymotion, Rumble, YouTube) via AES-GCM.
        """
        series = self.get_series_detail(slug_or_url)

        # Match episode by ID or number
        target_ep: Optional[EpisodeSummary] = None
        for ep in series.episodes:
            if ep.id == episode_id_or_num:
                target_ep = ep
                break
            try:
                if ep.episode_number == float(episode_id_or_num):
                    target_ep = ep
                    break
            except ValueError:
                pass

        if not target_ep:
            # Fallback to first episode or synthesize
            if series.episodes:
                target_ep = series.episodes[0]
            else:
                target_ep = EpisodeSummary(
                    episode_number=1.0,
                    id=f"{series.slug}-tab-1-ep-1",
                    title="Episode 1",
                    url=f"{PRIMARY_DOMAIN}/anime/{series.slug}?season=tab-1&episode={series.slug}-tab-1-ep-1",
                    season_id="tab-1",
                    primary_tab_id="primary-1"
                )

        # Decrypt real streaming servers
        servers = self.resolver.resolve_episode_sources(
            slug=series.slug,
            episode_id=target_ep.id,
            primary_tab_id=target_ep.primary_tab_id or "primary-1",
            season_id=target_ep.season_id or "tab-1"
        )

        ep_detail = RscParser.build_episode_detail(series, target_ep, servers=servers)
        self.storage.save_episode_detail(ep_detail)
        return ep_detail

    def crawl_series(
        self,
        slug_or_url: str,
        max_episodes: Optional[int] = None,
        resolve_streams: bool = True
    ) -> SeriesDetail:
        """
        Crawls and registers a series and all its episodes into SQLite database.
        If resolve_streams is True, resolves and decrypts stream sources for each episode.
        """
        series = self.get_series_detail(slug_or_url)
        target_episodes = series.episodes
        if max_episodes:
            target_episodes = target_episodes[:max_episodes]

        for ep in target_episodes:
            servers = None
            if resolve_streams:
                servers = self.resolver.resolve_episode_sources(
                    slug=series.slug,
                    episode_id=ep.id,
                    primary_tab_id=ep.primary_tab_id or "primary-1",
                    season_id=ep.season_id or "tab-1"
                )
            ep_detail = RscParser.build_episode_detail(series, ep, servers=servers)
            self.storage.save_episode_detail(ep_detail)

        return series
