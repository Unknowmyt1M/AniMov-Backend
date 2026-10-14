"""Data models for HDHub4u Scraper using Pydantic v2."""

from typing import List, Optional
from pydantic import BaseModel, Field


class HDHub4uSearchResult(BaseModel):
    """Search or catalog result item."""
    title: str
    link: str
    slug: str
    poster: Optional[str] = None
    media_type: str = "movie"  # 'movie' or 'series'
    year: Optional[str] = None
    quality_tag: Optional[str] = None


class HDHub4uDownloadLink(BaseModel):
    """Stream or download link option (HubDrive, HubCloud, HubCDN, PixelDrain, etc.)."""
    label: str
    url: str
    quality: Optional[str] = None
    size: Optional[str] = None
    provider: str = "HubDrive"


class HDHub4uEpisode(BaseModel):
    """Episode metadata with download/stream options."""
    episode_num: int
    title: str
    links: List[HDHub4uDownloadLink] = Field(default_factory=list)


class HDHub4uDetail(BaseModel):
    """Full details of a movie or web series."""
    title: str
    slug: str
    link: str
    media_type: str  # 'movie' or 'series'
    poster: Optional[str] = None
    synopsis: Optional[str] = None
    imdb_rating: Optional[str] = None
    audio: Optional[str] = None
    qualities_available: List[str] = Field(default_factory=list)
    movie_links: List[HDHub4uDownloadLink] = Field(default_factory=list)
    episodes: List[HDHub4uEpisode] = Field(default_factory=list)
