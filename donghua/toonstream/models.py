"""Data models for Toonstream Scraper using Pydantic v2."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ToonstreamSearchResult(BaseModel):
    """Search or catalog result item."""
    title: str
    link: str
    slug: str
    poster: Optional[str] = None
    media_type: str = "series"  # 'series' or 'movies'
    score: Optional[str] = None


class ToonstreamStreamServer(BaseModel):
    """Stream option/server from player embed."""
    server_name: str
    embed_url: str
    inner_iframe_url: Optional[str] = None


class ToonstreamEpisode(BaseModel):
    """Episode metadata."""
    title: str
    episode_code: str  # e.g. '1x1'
    season_num: int = 1
    episode_num: int = 1
    link: str
    thumbnail: Optional[str] = None
    stream_servers: List[ToonstreamStreamServer] = Field(default_factory=list)


class ToonstreamSeason(BaseModel):
    """Season information with episode list."""
    season_num: int
    title: str
    data_url: str
    episodes: List[ToonstreamEpisode] = Field(default_factory=list)


class ToonstreamDetail(BaseModel):
    """Complete detail for a series or movie."""
    title: str
    slug: str
    link: str
    media_type: str  # 'series' or 'movies'
    poster: Optional[str] = None
    backdrop: Optional[str] = None
    synopsis: Optional[str] = None
    cast: List[str] = Field(default_factory=list)
    duration: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    seasons: List[ToonstreamSeason] = Field(default_factory=list)
    movie_streams: List[ToonstreamStreamServer] = Field(default_factory=list)
