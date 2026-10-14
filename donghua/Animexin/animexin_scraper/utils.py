"""Small shared helpers."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

_NON_BREAKING = [" ", " ", " ", " ", " ", "​", "﻿"]


def normalize_text(text: str) -> str:
    if not text:
        return ""
    for ch in _NON_BREAKING:
        text = text.replace(ch, " ")
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).strip()


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html or "", "lxml")


def abs_url(base: str, href: str) -> str:
    if not href:
        return ""
    href = href.strip()
    if href.startswith("//"):
        href = "https:" + href
    if href.startswith("#") or href.startswith("javascript:"):
        return ""
    return urljoin(base, href)


def normalize_url(url: str) -> str:
    if not url:
        return ""
    p = urlparse(url)
    return urlunparse((p.scheme, p.netloc, p.path, p.params, p.query, ""))


def is_http_url(url: str) -> bool:
    try:
        p = urlparse(url)
    except Exception:
        return False
    return p.scheme in ("http", "https") and bool(p.netloc)


def dedupe_title(title: str) -> str:
    """AnimeXin sometimes duplicates titles ('Martial MasterMartial Master')."""
    t = normalize_text(title)
    if len(t) > 4 and len(t) % 2 == 0:
        half = len(t) // 2
        if t[:half] == t[half:]:
            return t[:half]
    return t


def slugify(title: str) -> str:
    s = normalize_text(title).lower()
    s = re.sub(r"[\(\)\[\]\{\}:;,.\?!\"]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s
