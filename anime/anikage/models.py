"""Data models for Anikage Anime Scraper using Pydantic v2."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AnikageSearchResult(BaseModel):
    """Anime search or catalog item."""
    slug: str
    romaji: str
    english: Optional[str] = None
    native: Optional[str] = None
    display_title: str
    poster: Optional[str] = None
    format: Optional[str] = "TV"
    status: Optional[str] = None
    score: Optional[float] = None
    genres: List[str] = Field(default_factory=list)


class AnikageSubtitle(BaseModel):
    """Subtitle track."""
    label: str
    file: str
    lang: str = "en"


class AnikageStreamSource(BaseModel):
    """Stream source item (m3u8, direct stream, embed)."""
    provider_id: str
    quality: Optional[str] = None
    url: str
    is_m3u8: bool = False
    stream_type: str = "sub"  # 'sub' or 'dub'


class AnikageEpisode(BaseModel):
    """Episode metadata."""
    id: str
    slug: str
    number: int
    title: Optional[str] = None
    season_number: int = 1
    air_date: Optional[str] = None
    rating: Optional[float] = None
    thumbnail: Optional[str] = None
    description: Optional[str] = None


class AnikageDetail(BaseModel):
    """Complete anime series detail."""
    slug: str
    romaji: str
    english: Optional[str] = None
    native: Optional[str] = None
    display_title: str
    poster: Optional[str] = None
    banner: Optional[str] = None
    synopsis: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    format: Optional[str] = None
    status: Optional[str] = None
    year: Optional[int] = None
    score: Optional[float] = None
    total_episodes: int = 0
    episodes: List[AnikageEpisode] = Field(default_factory=list)
