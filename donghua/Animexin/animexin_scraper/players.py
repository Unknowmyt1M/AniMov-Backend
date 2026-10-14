"""Embed / player URL extraction and provider classification for AnimeXin.

Episode pages expose mirrors as:
  <select class="mirror ..."><option value="<base64>">Server Name</option>...

Each base64 value decodes to an HTML snippet (usually an <iframe>).
We also inspect #pembed for direct iframes / Dailymotion meta / video tags.
tickcounter.com links are placeholders and are always skipped.
"""
from __future__ import annotations

import base64
import re
from typing import Optional

from bs4 import BeautifulSoup

from .utils import abs_url, make_soup, normalize_url

PEMBED = "#pembed"

_PROVIDER_PATTERNS = [
    (re.compile(r"(^|\.)dailymotion\.com$"), "dailymotion"),
    (re.compile(r"geo\.dailymotion\.com"), "dailymotion"),
    (re.compile(r"(^|\.)rumble\.com$"), "rumble"),
    (re.compile(r"(^|\.)ok\.ru$"), "ok.ru"),
    (re.compile(r"yurn\.online"), "yurn"),
    (re.compile(r"misterdonghua\.in"), "misterdonghua"),
    (re.compile(r"(^|\.)vidoza\.net$"), "vidoza"),
    (re.compile(r"(^|\.)vidhide\.com$"), "vidhide"),
    (re.compile(r"(^|\.)mp4upload\.com$"), "mp4upload"),
    (re.compile(r"(^|\.)streamtape\.com$"), "streamtape"),
    (re.compile(r"(^|\.)filemoon\."), "filemoon"),
    (re.compile(r"(^|\.)youtube\.com$"), "youtube"),
    (re.compile(r"(^|\.)youtu\.be$"), "youtube"),
    (re.compile(r"(^|\.)gdriveplayer\."), "gdriveplayer"),
    (re.compile(r"(^|\.)gdplayer\."), "gdplayer"),
    (re.compile(r"(^|\.)streamwish\."), "streamwish"),
]

_REGISTERED_DOMAIN = re.compile(r"([^.]+\.[^.]+)$")
_PLACEHOLDER = re.compile(r"tickcounter\.com", re.I)


def classify_provider(url: str) -> str:
    host = _hostname(url)
    if not host:
        return "unknown"
    for pattern, name in _PROVIDER_PATTERNS:
        if pattern.search(host):
            return name
    m = _REGISTERED_DOMAIN.search(host)
    return m.group(1).lower() if m else host.lower()


def _hostname(url: str) -> str:
    from urllib.parse import urlparse
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""


def is_placeholder(url: str) -> bool:
    return bool(_PLACEHOLDER.search(url or ""))


def decode_mirror_value(value: str) -> str:
    """Decode a select.mirror option value to an embed URL (or '')."""
    v = (value or "").strip()
    if not v:
        return ""
    if v.startswith("http") or v.startswith("//"):
        return v
    try:
        padded = v + "=" * (-len(v) % 4)
        decoded = base64.b64decode(padded).decode("utf-8", errors="ignore")
    except Exception:
        return ""
    soup = BeautifulSoup(decoded, "html.parser")
    iframe = soup.find("iframe")
    if iframe and iframe.get("src"):
        return iframe["src"].strip()
    # sometimes decoded payload is a bare URL
    m = re.search(r"https?://[^\s\"'<>]+", decoded)
    return m.group(0) if m else ""


def extract_servers_from_soup(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """Extract {label, url} mirrors from select.mirror options."""
    servers: list[dict] = []
    for i, opt in enumerate(soup.select("select.mirror option, select[class*=mirror] option, select[class*=server] option")):
        value = (opt.get("value") or "").strip()
        if not value:
            continue
        from .utils import normalize_text
        label = normalize_text(opt.get_text(" ", strip=True))
        decoded = decode_mirror_value(value)
        target = decoded or (value if value.startswith("http") else "")
        if not target:
            continue
        url = abs_url(base_url, target)
        if not url or is_placeholder(url):
            continue
        servers.append({"label": label, "url": normalize_url(url), "index": i})
    return servers


def extract_embeds_from_soup(soup: BeautifulSoup, base_url: str) -> list[dict]:
    embeds: list[dict] = []
    seen: set[str] = set()

    def add(url: str, origin: str = "static", server_label: str = "") -> None:
        u = abs_url(base_url, (url or "").strip())
        if not u or is_placeholder(u):
            return
        u = normalize_url(u)
        if u in seen:
            return
        seen.add(u)
        embeds.append({"provider": classify_provider(u), "url": u,
                       "origin": origin, "server_label": server_label})

    pe = soup.select_one(PEMBED) or soup.select_one("#embed_holder")
    scope = pe if pe is not None else soup
    # 1. direct iframes (skip ad iframes outside #pembed when container exists)
    for iframe in scope.select("iframe[src]"):
        add(iframe.get("src", ""))
    for meta in scope.select('meta[itemprop="embedUrl"], meta[itemprop="contentUrl"]'):
        add(meta.get("content", ""))
    for vid in scope.select("video source[src], video[src]"):
        add(vid.get("src", ""))
    for sc in scope.select("script[data-video]"):
        video_id = (sc.get("data-video") or "").strip()
        src = (sc.get("src") or "").strip()
        if not video_id:
            continue
        m = re.search(r"player/([a-zA-Z0-9_-]+)\.js", src)
        if m:
            add(f"https://geo.dailymotion.com/player/{m.group(1)}.html?video={video_id}")
        else:
            add(f"https://www.dailymotion.com/embed/video/{video_id}")
    # 2. mirror options decoded
    for srv in extract_servers_from_soup(soup, base_url):
        add(srv["url"], origin="static", server_label=srv["label"])
    return embeds


def extract_embeds_from_html(html: str, base_url: str) -> list[dict]:
    return extract_embeds_from_soup(make_soup(html), base_url)
