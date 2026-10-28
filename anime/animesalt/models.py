"""Data models for AnimeSalt Scraper using Pydantic v2."""

from typing import List, Optional
from pydantic import BaseModel, Field


class AnimeSaltSearchResult(BaseModel):
    """Search result item."""
    slug: str
    title: str
    poster: Optional[str] = None
    anime_type: Optional[str] = "TV Series"
    episodes: Optional[str] = "Series"
    duration: Optional[str] = "~24m / ep"
    link: str


class AnimeSaltAudioStream(BaseModel):
    """Multi-audio stream option (Hindi, Tamil, Telugu, English, etc.)."""
    language: str
    link: str


class AnimeSaltEpisode(BaseModel):
    """Episode metadata."""
    slug: str
    episode_num: int
    season_num: int = 1
    title: str
    link: str
    iframe_url: Optional[str] = None
    audio_streams: List[AnimeSaltAudioStream] = Field(default_factory=list)


class AnimeSaltSeriesDetail(BaseModel):
    """Anime series metadata and episode catalog."""
    slug: str
    title: str
    poster: Optional[str] = None
    synopsis: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    duration: Optional[str] = None
    year: Optional[str] = None
    rating: Optional[str] = None
    status: Optional[str] = None
    total_episodes: int = 0
    total_seasons: Optional[int] = None
    seasons: List[int] = Field(default_factory=list)
    episodes: List[AnimeSaltEpisode] = Field(default_factory=list)


class AnimeSaltCrawlStats(BaseModel):
    """Crawl & cache statistics."""
    total_series: int = 0
    total_episodes: int = 0
    total_streams: int = 0
    last_crawled_at: Optional[str] = None
