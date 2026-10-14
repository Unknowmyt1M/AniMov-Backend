"""
Pydantic v2 data models for AnimeCube Next.js scraper.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class StreamServer(BaseModel):
    server_name: str
    provider: str
    embed_url: str
    quality: Optional[str] = "1080p / 4K"
    languages: List[str] = Field(default_factory=lambda: ["Multi-Sub", "English"])
    platform: Optional[str] = None
    video_id: Optional[str] = None
    private_id: Optional[str] = None
    good_sub: Optional[bool] = None
    extra_data: Dict[str, Any] = Field(default_factory=dict)


class EpisodeSummary(BaseModel):
    episode_number: float
    id: str
    title: str
    url: str
    season_id: Optional[str] = "tab-1"
    primary_tab_id: Optional[str] = "primary-1"
    duration: Optional[int] = None
    published_at: Optional[str] = None
    thumbnail: Optional[str] = None


class EpisodeDetail(BaseModel):
    episode_number: float
    id: str
    title: str
    url: str
    series_slug: str
    series_title: Optional[str] = None
    season_id: Optional[str] = "tab-1"
    primary_tab_id: Optional[str] = "primary-1"
    duration: Optional[int] = None
    published_at: Optional[str] = None
    servers: List[StreamServer] = Field(default_factory=list)
    prev_episode: Optional[str] = None
    next_episode: Optional[str] = None


class SeriesDetail(BaseModel):
    slug: str
    url: str
    title: str
    aliases: List[str] = Field(default_factory=list)
    rating: Optional[str] = None
    status: Optional[str] = None
    year: Optional[int] = None
    total_episodes: Optional[int] = None
    genres: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    synopsis: Optional[str] = None
    cover_image: Optional[str] = None
    update_days: List[str] = Field(default_factory=list)
    update_time: Optional[str] = None
    episodes: List[EpisodeSummary] = Field(default_factory=list)
    extra_meta: Dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    title: str
    slug: str
    url: str
    status: Optional[str] = None
    year: Optional[int] = None
    cover_image: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    total_episodes: Optional[int] = None


class CrawlStats(BaseModel):
    total_series: int = 0
    total_episodes: int = 0
    completed_episodes: int = 0
    pending_episodes: int = 0
    failed_episodes: int = 0
