"""Data models for 1Tube Scraper."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MovieSearchResult(BaseModel):
    """1Tube search result item."""
    id: str  # TMDB ID
    title: str
    media_type: str  # "Movie" or "TV Series"
    release_year: Optional[str] = None
    poster: Optional[str] = None
    score: Optional[str] = None
    overview: Optional[str] = None
    link: str


class StreamSource(BaseModel):
    """Streaming mirror for 1Tube."""
    server_name: str
    embed_url: str
    source_type: str = "iframe"
    headers: Dict[str, str] = Field(default_factory=dict)


class MovieDetail(BaseModel):
    """Comprehensive details for 1Tube title."""
    id: str
    title: str
    original_title: Optional[str] = None
    media_type: str = "Movie"
    release_year: Optional[str] = None
    duration: Optional[str] = None
    rating: Optional[str] = None
    vote_count: Optional[int] = None
    genres: List[str] = Field(default_factory=list)
    synopsis: Optional[str] = None
    tagline: Optional[str] = None
    poster: Optional[str] = None
    backdrop: Optional[str] = None
    streams: List[StreamSource] = Field(default_factory=list)
    watch_url: str
