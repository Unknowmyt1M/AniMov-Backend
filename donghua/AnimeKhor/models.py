"""
Pydantic v2 data models for AnimeKhor scraper.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class StreamServer(BaseModel):
    server_name: str
    provider: str
    embed_url: str
    quality: Optional[str] = "Auto"
    languages: List[str] = Field(default_factory=list)


class DownloadOption(BaseModel):
    title: str
    host: Optional[str] = None
    url: str
    quality: Optional[str] = None


class EpisodeSummary(BaseModel):
    episode_number: float
    title: str
    url: str
    release_date: Optional[str] = None


class EpisodeDetail(BaseModel):
    episode_number: float
    title: str
    url: str
    release_date: Optional[str] = None
    series_title: Optional[str] = None
    series_url: Optional[str] = None
    servers: List[StreamServer] = Field(default_factory=list)
    downloads: List[DownloadOption] = Field(default_factory=list)
    prev_episode: Optional[str] = None
    next_episode: Optional[str] = None


class SeriesDetail(BaseModel):
    slug: str
    url: str
    title: str
    native_title: Optional[str] = None
    rating: Optional[str] = None
    status: Optional[str] = None
    studio: Optional[str] = None
    country: Optional[str] = None
    released_date: Optional[str] = None
    duration: Optional[str] = None
    season: Optional[str] = None
    type_name: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    synopsis: Optional[str] = None
    poster: Optional[str] = None
    episodes: List[EpisodeSummary] = Field(default_factory=list)
    extra_meta: Dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    title: str
    slug: str
    url: str
    type_name: Optional[str] = None
    latest_ep: Optional[str] = None
    poster: Optional[str] = None
    rating: Optional[str] = None


class CrawlStats(BaseModel):
    total_series: int = 0
    total_episodes: int = 0
    completed_episodes: int = 0
    pending_episodes: int = 0
    failed_episodes: int = 0
