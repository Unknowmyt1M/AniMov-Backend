"""
Strongly-typed Pydantic schemas for Lucifer Donghua Scraper.
Supports full show metadata, characters/voice actors, episode listings,
server mirrors (4K/1080p, Dailymotion, Rumble, OK.ru, VidHide), and direct downloads.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CharacterItem(BaseModel):
    """Character and voice actor details associated with the Donghua."""
    name: str = Field(..., description="Character name e.g. Dou, Zhanlong")
    role: str = Field(default="Supporting", description="Main or Supporting")
    image_url: Optional[str] = Field(default=None, description="Character avatar/thumbnail")


class LuciferDownloadOption(BaseModel):
    """Direct download link extracted from episode pages."""
    title: Optional[str] = Field(default=None, description="Download label or file name")
    host: str = Field(default="MisterDonghua", description="Hosting service or download portal")
    url: str = Field(..., description="Direct download portal link")


class LuciferStreamServer(BaseModel):
    """Streaming video server option from Lucifer Donghua's mirror dropdown."""
    server_name: str = Field(..., description="Display label e.g. [4K] Eng [RUBMLE - Server]")
    provider: str = Field(..., description="Normalized host: dailymotion, rumble, vidhide, ok.ru, etc.")
    quality: str = Field(default="4K", description="Resolution tag: 4K, 1080p")
    languages: List[str] = Field(default_factory=list, description="Sub languages: English, Indonesian")
    server_url: str = Field(..., description="Internal server route e.g. /v/2/")
    embed_url: Optional[str] = Field(default=None, description="Resolved iframe embed source")
    is_default: bool = Field(default=False, description="Whether this is the default initial server")
    direct_stream_url: Optional[str] = Field(default=None, description="Direct .m3u8/.mp4 stream URL if sniffed")


class LuciferEpisodeListItem(BaseModel):
    """Episode summary item from the series page episode table."""
    episode_number: float = Field(..., description="Parsed float episode number (handles ranges like 4.0 for 04 & 05)")
    raw_number_text: str = Field(..., description="Original raw text e.g. '09 [4K]', '04 & 05 [4K]'")
    title: str = Field(..., description="Episode title e.g. 'Golden Curse Episode 09 English Sub'")
    sub_type: str = Field(default="Sub", description="Sub / Raw / Dub")
    quality_tag: str = Field(default="4K", description="4K or 1080p")
    release_date: Optional[str] = Field(default=None, description="Release date text e.g. 'September 27, 2026'")
    url: str = Field(..., description="Direct link to episode page")


class LuciferEpisodeDetail(BaseModel):
    """Comprehensive playback and metadata for an individual episode page."""
    episode_title: str = Field(..., description="Episode title from h1.entry-title")
    episode_number: float = Field(..., description="Parsed numeric episode number")
    release_date: Optional[str] = Field(default=None, description="Publication date or ISO timestamp")
    views: Optional[str] = Field(default=None, description="View count e.g. '60097 views'")
    posted_by: Optional[str] = Field(default=None, description="Uploader or author")
    series_title: Optional[str] = Field(default=None, description="Parent series title")
    series_url: Optional[str] = Field(default=None, description="Parent series canonical URL")
    prev_episode_url: Optional[str] = Field(default=None, description="Previous episode URL")
    next_episode_url: Optional[str] = Field(default=None, description="Next episode URL")
    default_embed: Optional[str] = Field(default=None, description="Default player iframe embed URL")
    servers: List[LuciferStreamServer] = Field(default_factory=list, description="All available streaming server mirrors")
    downloads: List[LuciferDownloadOption] = Field(default_factory=list, description="Direct download links")
    source_url: str = Field(..., description="Source episode URL")


class LuciferDonghuaDetail(BaseModel):
    """Complete metadata for a Lucifer Donghua series."""
    title: str = Field(..., description="Primary English title e.g. Golden Curse (2026)")
    alternative_titles: Optional[str] = Field(default=None, description="Chinese & alternate titles e.g. 财神窦占龙")
    slug: str = Field(..., description="Series slug")
    rating: Optional[str] = Field(default=None, description="Rating e.g. 8.0")
    followers: Optional[str] = Field(default=None, description="Follower count e.g. 70 people")
    poster_url: Optional[str] = Field(default=None, description="High-resolution poster image")
    status: Optional[str] = Field(default=None, description="Ongoing | Completed | Upcoming")
    studio: Optional[str] = Field(default=None, description="Animation studio e.g. CG Year")
    released_year: Optional[str] = Field(default=None, description="Release date text e.g. Aug 16, 2026")
    duration: Optional[str] = Field(default=None, description="Duration per episode e.g. 21 min per ep.")
    country: Optional[str] = Field(default="China", description="Country of origin")
    type: Optional[str] = Field(default="ONA", description="ONA | DONGHUA | TV | MOVIE | OVA")
    total_episodes_expected: Optional[str] = Field(default=None, description="Expected episode count e.g. 16")
    fansub: Optional[str] = Field(default=None, description="Fansub group e.g. Lucifer Donghua")
    director: Optional[str] = Field(default=None, description="Director e.g. Xu Zheng")
    producers: List[str] = Field(default_factory=list, description="Producers e.g. ['bilibili', 'iQIYI']")
    posted_by: Optional[str] = Field(default=None, description="Author/admin")
    site_released_on: Optional[str] = Field(default=None, description="Site publish date")
    site_updated_on: Optional[str] = Field(default=None, description="Site last update date")
    genres: List[str] = Field(default_factory=list, description="List of genres")
    tags: List[str] = Field(default_factory=list, description="Search tags")
    synopsis: Optional[str] = Field(default=None, description="Full synopsis description")
    characters: List[CharacterItem] = Field(default_factory=list, description="Characters and voice actors list")
    first_episode_url: Optional[str] = Field(default=None, description="Episode 1 URL")
    latest_episode_url: Optional[str] = Field(default=None, description="Latest episode URL")
    total_scraped_episodes: int = Field(default=0, description="Count of scraped episodes")
    episodes: List[LuciferEpisodeListItem] = Field(default_factory=list, description="Discovered episode items")
    source_url: str = Field(..., description="Canonical series URL")


class LuciferCatalogCard(BaseModel):
    """Brief series card from catalog browse or search."""
    title: str = Field(..., description="Series title")
    slug: str = Field(..., description="Series slug")
    url: str = Field(..., description="Series page URL")
    poster_url: Optional[str] = Field(default=None, description="Poster image URL")
    type: Optional[str] = Field(default="ONA", description="Media type")
    status: Optional[str] = Field(default=None, description="Ongoing / Completed")
    latest_episode: Optional[str] = Field(default=None, description="Latest episode label")
