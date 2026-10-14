"""
Pydantic v2 data models for the Miruro Anime scraper.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SubtitleTrack(BaseModel):
    language: str
    label: str
    file: str
    format: Optional[str] = "vtt"
    default: bool = False


class StreamMirror(BaseModel):
    server_name: str
    provider: str
    track_type: str = "sub"  # "sub", "ssub", "dub"
    format: str = "hls"  # "hls", "mp4", "embed"
    url: Optional[str] = None
    embed_url: Optional[str] = None
    quality: Optional[str] = "1080p / Multi-Quality"
    raw_upstream_url: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    extra_data: Dict[str, Any] = Field(default_factory=dict)


class EpisodeSummary(BaseModel):
    id: str
    episode_number: float
    title: str
    thumbnail_url: Optional[str] = None
    duration_minutes: Optional[int] = None
    aired_at: Optional[str] = None


class EpisodeDetail(BaseModel):
    id: str
    anime_id: str
    episode_number: float
    title: str
    thumbnail_url: Optional[str] = None
    subtitles: List[SubtitleTrack] = Field(default_factory=list)
    servers: List[StreamMirror] = Field(default_factory=list)
    downloads: List[Dict[str, Any]] = Field(default_factory=list)
    prev_episode: Optional[float] = None
    next_episode: Optional[float] = None


class SeriesDetail(BaseModel):
    id: str
    title_english: Optional[str] = None
    title_romaji: Optional[str] = None
    title_native: Optional[str] = None
    format: Optional[str] = None
    status: Optional[str] = None
    season: Optional[str] = None
    season_year: Optional[int] = None
    episode_count: Optional[int] = None
    average_score: Optional[float] = None
    popularity: Optional[int] = None
    cover_url: Optional[str] = None
    banner_url: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    studios: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    episodes: List[EpisodeSummary] = Field(default_factory=list)
    external_ids: Dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    id: str
    title: str
    title_romaji: Optional[str] = None
    format: Optional[str] = None
    status: Optional[str] = None
    year: Optional[int] = None
    episode_count: Optional[int] = None
    duration: Optional[str] = None
    average_score: Optional[float] = None
    cover_url: Optional[str] = None
    genres: List[str] = Field(default_factory=list)


class CrawlStats(BaseModel):
    total_series: int = 0
    total_episodes: int = 0
    completed_episodes: int = 0
    pending_episodes: int = 0
    failed_episodes: int = 0
