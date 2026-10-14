"""Data models for WatchAnimeWorld Scraper using Pydantic v2."""

from typing import List, Optional
from pydantic import BaseModel, Field


class WatchAnimeWorldSearchResult(BaseModel):
    """Search result item."""
    slug: str
    title: str
    poster: Optional[str] = None
    media_type: str = "series"  # series or movie
    episodes: Optional[str] = "Hindi Dubbed Series"
    duration: Optional[str] = "~24m / ep"
    link: str


class WatchAnimeWorldServer(BaseModel):
    """Streaming server mirror or embed."""
    name: str
    embed_url: str


class WatchAnimeWorldEpisode(BaseModel):
    """Episode metadata."""
    slug: str
    episode_num: int
    season_num: int = 1
    title: str
    link: str
    servers: List[WatchAnimeWorldServer] = Field(default_factory=list)


class WatchAnimeWorldSeriesDetail(BaseModel):
    """Anime series metadata and episode catalog."""
    slug: str
    title: str
    poster: Optional[str] = None
    synopsis: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    year: Optional[str] = None
    rating: Optional[str] = None
    status: Optional[str] = None
    total_episodes: int = 0
    episodes: List[WatchAnimeWorldEpisode] = Field(default_factory=list)


class WatchAnimeWorldCrawlStats(BaseModel):
    """Crawl & cache statistics."""
    total_series: int = 0
    total_episodes: int = 0
    total_streams: int = 0
    last_crawled_at: Optional[str] = None
