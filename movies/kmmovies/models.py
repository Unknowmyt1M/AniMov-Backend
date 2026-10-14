"""Data models for KMMovies Scraper."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MovieSearchResult(BaseModel):
    """KMMovies search result item."""
    id: str
    slug: str
    title: str
    poster: Optional[str] = None
    media_type: str = "Movie"
    release_year: Optional[str] = None
    qualities: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    link: str


class DownloadSource(BaseModel):
    """Download / Stream mirror."""
    quality: str
    size: Optional[str] = None
    url: str
    label: str


class MovieDetail(BaseModel):
    """Full KMMovies movie/series details."""
    id: str
    slug: str
    title: str
    poster: Optional[str] = None
    media_type: str = "Movie"
    release_year: Optional[str] = None
    duration: Optional[str] = None
    rating: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    genres: List[str] = Field(default_factory=list)
    synopsis: Optional[str] = None
    downloads: List[DownloadSource] = Field(default_factory=list)
    page_url: str
