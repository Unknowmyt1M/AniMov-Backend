"""Data models for ReAnime Scraper using Pydantic v2."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ReAnimeSearchResult(BaseModel):
    """Search result item."""
    slug: str
    title: str
    poster: Optional[str] = None
    anime_type: Optional[str] = None
    episodes: Optional[str] = None
    duration: Optional[str] = None
    score: Optional[str] = None
    link: str


class ReAnimeEpisode(BaseModel):
    """Episode metadata with rich SvelteKit tags."""
    id: str  # e.g. "ep-1"
    episode_num: int
    title: str
    is_subbed: bool = True
    is_dubbed: bool = False
    is_filler: bool = False
    is_recap: bool = False
    aired_at: Optional[str] = None
    playable: bool = True


class ReAnimeStreamResult(BaseModel):
    """Episode streaming server / player details."""
    slug: str
    episode_num: int
    embed_url: Optional[str] = None
    status: str = "available"  # "available" or "upstream_sources_pending"
    message: Optional[str] = None
    raw_sources: Optional[Dict[str, Any]] = None


class ReAnimeSeriesDetail(BaseModel):
    """Rich anime metadata combining AniList/TMDB and ReAnime catalog."""
    slug: str
    title: str
    english_title: Optional[str] = None
    native_title: Optional[str] = None
    romaji_title: Optional[str] = None
    anilist_id: Optional[int] = None
    mal_id: Optional[int] = None
    poster: Optional[str] = None
    banner: Optional[str] = None
    synopsis: Optional[str] = None
    anime_type: Optional[str] = None
    status: Optional[str] = None
    season: Optional[str] = None
    season_year: Optional[int] = None
    genres: List[str] = Field(default_factory=list)
    average_score: Optional[int] = None
    total_episodes: int = 0
    episodes: List[ReAnimeEpisode] = Field(default_factory=list)


class ReAnimeCrawlStats(BaseModel):
    """Crawl & cache statistics."""
    total_series: int = 0
    total_episodes: int = 0
    total_streams: int = 0
    last_crawled_at: Optional[str] = None
