"""Parsed data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AnimeCard:
    url: str
    title: str
    poster_url: str = ""
    card_type: str = ""
    status: str = ""


@dataclass
class ListingPage:
    cards: list[AnimeCard] = field(default_factory=list)
    next_url: Optional[str] = None


@dataclass
class EpisodeEntry:
    url: str
    raw_label: str
    title: str
    release_date: str = ""
    subtitle_lang: str = ""
    dom_order: int = 0
    data_index: str = ""


@dataclass
class DetailPage:
    url: str
    title: str = ""
    poster_url: str = ""
    synopsis: str = ""
    genres: list[str] = field(default_factory=list)
    rating: str = ""
    quality: list[str] = field(default_factory=list)
    audio: list[str] = field(default_factory=list)
    status: str = ""
    anime_type: str = ""
    site_episode_count: Optional[int] = None
    episodes: list[EpisodeEntry] = field(default_factory=list)


@dataclass
class ServerOption:
    label: str
    url: str
    index: int


@dataclass
class Embed:
    provider: str
    url: str
    origin: str = "static"
    server_label: str = ""


@dataclass
class EpisodePage:
    url: str
    title: str = ""
    servers: list[ServerOption] = field(default_factory=list)
    embeds: list[Embed] = field(default_factory=list)
