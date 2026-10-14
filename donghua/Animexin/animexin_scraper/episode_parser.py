"""Episode label parsing: (raw num cell, title cell) -> structured meta."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .utils import normalize_text

_QUALITY = re.compile(r"\[(4K|1080P?|720P?|480P?|HINDI|TAMIL|TELUGU|ENG|SUB|DUB)[^\]]*\]", re.I)
_BRACKETED = re.compile(r"\[[^\]]*\]")
_RANGE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:to|and|&|-|–|,|\+)\s*(\d+(?:\.\d+)?)", re.I)
_EP_N = re.compile(r"(?:episode|ep\.?)\s*(\d+(?:\.\d+)?)", re.I)
_PART = re.compile(r"(?:\bPT\b|part)[\s\-_]*0*(\d+)", re.I)
_SPECIAL = re.compile(r"special", re.I)
_MOVIE = re.compile(r"\bmovie\b", re.I)
_TRAILER = re.compile(r"\b(trailer|pv|teaser)\b", re.I)
_CHAPTER = re.compile(r"chapter|middle\s*ch", re.I)
_OVA = re.compile(r"\bova\b|\bona\b", re.I)


@dataclass
class EpisodeMeta:
    episode_number: Optional[int | float] = None
    part: Optional[int] = None
    episode_type: str = "episode"
    episode_title: str = ""
    raw_label: str = ""
    range_start: Optional[int | float] = None
    range_end: Optional[int | float] = None


def parse_episode_label(raw_label: str, title: str = "") -> EpisodeMeta:
    raw = normalize_text(raw_label)
    t = normalize_text(title)
    meta = EpisodeMeta(raw_label=raw, episode_title=t)

    low = f"{raw} {t}".lower()
    if _TRAILER.search(low):
        meta.episode_type = "trailer"
    elif _MOVIE.search(low):
        meta.episode_type = "movie"
    elif _SPECIAL.search(low):
        meta.episode_type = "special"
    elif _CHAPTER.search(low):
        meta.episode_type = "chapter"
    elif _OVA.search(low):
        meta.episode_type = "ova"

    m_part = _PART.search(t) or _PART.search(raw)
    if m_part:
        try:
            meta.part = int(m_part.group(1))
        except ValueError:
            pass

    # Prefer explicit "Episode N" in title (num cell is occasionally off-by-one)
    m_ep = _EP_N.search(t)
    num: Optional[int | float] = None
    if m_ep:
        v = m_ep.group(1)
        num = float(v) if "." in v else int(v)
    else:
        cleaned = _BRACKETED.sub(" ", raw)
        m_num = re.search(r"(\d+(?:\.\d+)?)", cleaned)
        if m_num:
            v = m_num.group(1)
            num = float(v) if "." in v else int(v)

    # Range detection from title first, then num cell
    m_range = _RANGE.search(t) or _RANGE.search(raw)
    if m_range:
        try:
            r1, r2 = m_range.group(1), m_range.group(2)
            meta.range_start = float(r1) if "." in r1 else int(r1)
            meta.range_end = float(r2) if "." in r2 else int(r2)
            num = num if num is not None else meta.range_start
        except ValueError:
            pass

    if meta.episode_type == "movie" and num is None and meta.part is None:
        pass  # movies often have no number
    meta.episode_number = num
    if not t:
        meta.episode_title = raw or (f"Episode {num}" if num is not None else "Episode")
    return meta


def range_str(meta: EpisodeMeta) -> Optional[str]:
    if meta.range_start is not None and meta.range_end is not None:
        return f"{meta.range_start}-{meta.range_end}"
    return None
