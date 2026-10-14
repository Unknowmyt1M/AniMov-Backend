"""Data models for AnimeSuge Scraper using Pydantic v2."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AnimeSugeSearchResult(BaseModel):
    """Search item result model."""
    id: Optional[str] = None
    slug: str
    title: str
    poster: Optional[str] = None
    anime_type: Optional[str] = None
    episodes: Optional[str] = None
    duration: Optional[str] = None
    score: Optional[str] = None
    quality: Optional[str] = None
    link: str


class AnimeSugeSubtitleTrack(BaseModel):
    """Subtitle track representation."""
    file: str
    label: str
    kind: str = "captions"
    default: bool = False


class AnimeSugeSkipInterval(BaseModel):
    """Skip interval range in seconds."""
    start: Optional[int] = None
    end: Optional[int] = None


class AnimeSugeSkipData(BaseModel):
    """Intro and outro timestamps."""
    intro: Optional[AnimeSugeSkipInterval] = None
    outro: Optional[AnimeSugeSkipInterval] = None


class AnimeSugeServer(BaseModel):
    """Streaming server mirror option."""
    name: str
    link_id: str
    server_type: str = "sub"  # "sub" or "dub"
    embed_url: Optional[str] = None


class AnimeSugeEpisode(BaseModel):
    """Episode metadata in series catalog."""
    id: str
    episode_num: int
    slug: str
    title: str
    server_param: str = ""
    has_sub: bool = True
    has_dub: bool = False
    timestamp: Optional[int] = None
    servers: List[AnimeSugeServer] = Field(default_factory=list)


class AnimeSugeStreamResult(BaseModel):
    """Direct stream playback result with decrypted master m3u8."""
    episode_id: str
    episode_num: int
    server_name: str
    server_type: str  # "sub" or "dub"
    embed_url: str
    master_m3u8: Optional[str] = None
    subtitles: List[AnimeSugeSubtitleTrack] = Field(default_factory=list)
    skip_data: Optional[AnimeSugeSkipData] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    raw_sources: Optional[Dict[str, Any]] = None


class AnimeSugeSeriesDetail(BaseModel):
    """Comprehensive Anime series detail model."""
    anime_id: str
    slug: str
    title: str
    english_title: Optional[str] = None
    poster: Optional[str] = None
    synopsis: Optional[str] = None
    anime_type: Optional[str] = None
    status: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    total_episodes: int = 0
    episodes: List[AnimeSugeEpisode] = Field(default_factory=list)


class AnimeSugeCrawlStats(BaseModel):
    """Statistics on cached/crawled AnimeSuge records."""
    total_series: int = 0
    total_episodes: int = 0
    total_streams: int = 0
    last_crawled_at: Optional[str] = None
