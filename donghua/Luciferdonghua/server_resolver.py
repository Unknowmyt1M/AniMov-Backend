"""
Server Resolver for Lucifer Donghua.
Extracts server mirrors, routes (/v/1/, /v/2/), providers (Rumble, Dailymotion, VidHide, OK.ru),
quality tags, and direct download portals.
"""

import re
from typing import List, Optional, Tuple
from bs4 import BeautifulSoup

from .models import LuciferStreamServer, LuciferDownloadOption


PROVIDER_REGEX = [
    (re.compile(r"dailymotion", re.IGNORECASE), "dailymotion"),
    (re.compile(r"rubmle|rumble", re.IGNORECASE), "rumble"),
    (re.compile(r"vid\s*hide|yurn", re.IGNORECASE), "vidhide"),
    (re.compile(r"ok\.?ru", re.IGNORECASE), "ok.ru"),
    (re.compile(r"streamwish|wishembed", re.IGNORECASE), "streamwish"),
    (re.compile(r"dood", re.IGNORECASE), "doodstream"),
    (re.compile(r"mega", re.IGNORECASE), "mega"),
]


def classify_provider_name(text: str) -> str:
    """Identifies streaming provider from server title text."""
    for pattern, name in PROVIDER_REGEX:
        if pattern.search(text):
            return name
    return "generic"


def parse_mirror_options(soup: BeautifulSoup, base_url: str = "https://luciferdonghua.in") -> List[LuciferStreamServer]:
    """
    Parses <select class="mirror"> options into structured LuciferStreamServer instances.
    """
    servers: List[LuciferStreamServer] = []
    mirror_select = soup.find("select", class_=re.compile(r"mirror|server", re.IGNORECASE))
    if not mirror_select:
        return servers

    for idx, opt in enumerate(mirror_select.find_all("option"), start=1):
        name = opt.text.strip()
        val = opt.get("value", "").strip()

        if not val or name.lower() in ("select video server", "select server"):
            continue

        provider = classify_provider_name(name)

        # Detect quality
        quality = "4K" if "4k" in name.lower() else ("1080p" if "1080" in name.lower() else "HD")

        # Detect languages
        languages = []
        if "eng" in name.lower():
            languages.append("English")
        if "indo" in name.lower():
            languages.append("Indonesian")

        # Ensure full server URL
        full_server_url = val
        if val.startswith("/"):
            full_server_url = base_url.rstrip("/") + val

        servers.append(
            LuciferStreamServer(
                server_name=name,
                provider=provider,
                quality=quality,
                languages=languages,
                server_url=full_server_url,
                embed_url=None,
                is_default=(idx == 2),  # First valid option is usually default
            )
        )

    return servers


def extract_active_embed(soup: BeautifulSoup) -> Optional[str]:
    """
    Extracts the active video player iframe src from #pembed.
    Filters out fake ads and tracker iframes.
    """
    pembed = soup.select_one("#pembed, #embed_holder, .player-embed")
    if not pembed:
        return None

    # First check for video players (dailymotion, rumble, yurn, ok.ru)
    for iframe in pembed.find_all("iframe"):
        src = iframe.get("src", "").strip()
        if not src:
            continue
        # Check against known ad servers
        if any(ad in src for ad in ["a-ads.com", "adsgravity", "chagnougroalry", "cointraffic", "coinprediction"]):
            continue
        if src.startswith("//"):
            src = "https:" + src
        return src

    # Check for Dailymotion script/geo player tags
    for s in pembed.find_all("script"):
        video_id = s.get("data-video")
        if video_id:
            return f"https://geo.dailymotion.com/player/xbj0x.html?video={video_id}"

    return None


def extract_download_links(soup: BeautifulSoup) -> List[LuciferDownloadOption]:
    """Extracts direct download portal links (e.g. MisterDonghua)."""
    downloads: List[LuciferDownloadOption] = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(strip=True)

        if "misterdonghua" in href or ("download" in text.lower() and href.startswith("http")):
            if href not in seen:
                seen.add(href)
                downloads.append(
                    LuciferDownloadOption(
                        title=text or "Download Portal",
                        host="MisterDonghua" if "misterdonghua" in href else "External",
                        url=href
                    )
                )

    return downloads
