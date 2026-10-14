"""Data models for Hindilinks4u Movie Scraper."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MovieSearchResult(BaseModel):
    """Movie search result item."""
    id: str
    slug: str
    title: str
    poster: Optional[str] = None
    media_type: str = "Movie"
    release_year: Optional[str] = None
    duration: Optional[str] = None
    score: Optional[str] = None
    quality: Optional[str] = None
    link: str


class StreamSource(BaseModel):
    """Streaming embed / server mirror."""
    server_name: str
    embed_url: str
    source_type: str = "iframe"  # iframe, direct, m3u8
    quality: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)


class MovieDetail(BaseModel):
    """Full movie details."""
    id: str
    slug: str
    title: str
    alt_title: Optional[str] = None
    poster: Optional[str] = None
    media_type: str = "Movie"
    release_year: Optional[str] = None
    duration: Optional[str] = None
    rating: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    synopsis: Optional[str] = None
    directors: List[str] = Field(default_factory=list)
    cast: List[str] = Field(default_factory=list)
    country: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    streams: List[StreamSource] = Field(default_factory=list)
    trailer_url: Optional[str] = None
    page_url: str
