"""Catalog discovery: sitemap or walk /anime/ pagination with loop guard."""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

from .http_client import HttpClient, HtmlCache, fetch_cached
from .models import AnimeCard
from .parser import parse_listing
from .utils import normalize_url

log = logging.getLogger(__name__)


def discover_sitemap(http: HttpClient, cache: HtmlCache, source: str,
                     *, refresh: bool = False) -> list[AnimeCard]:
    """Discover anime catalog via /anime-sitemap.xml (instant 1-request catalog)."""
    sitemap_url = f"{source.rstrip('/')}/anime-sitemap.xml"
    try:
        xml_text = fetch_cached(http, cache, sitemap_url, refresh=refresh)
        root = ET.fromstring(xml_text)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
              "image": "http://www.google.com/schemas/sitemap-image/1.1"}
        cards: list[AnimeCard] = []
        for url_node in root.findall("sm:url", ns):
            loc = url_node.find("sm:loc", ns)
            if loc is None or not loc.text:
                continue
            card_url = loc.text.strip()
            # Skip the root /anime/ listing URL if present
            path = urlparse(card_url).path.strip("/")
            if not path or path == "anime":
                continue

            # Find poster if provided by sitemap
            img_loc = url_node.find("image:image/image:loc", ns)
            poster = img_loc.text.strip() if img_loc is not None and img_loc.text else ""

            # Derive clean initial title from slug (will be upgraded on detail parse)
            title = path.replace("-", " ").title()
            cards.append(AnimeCard(url=normalize_url(card_url), title=title, poster_url=poster))

        if cards:
            log.info("Discovered %d anime from sitemap (%s)", len(cards), sitemap_url)
            return cards
    except Exception as exc:
        log.warning("Sitemap discovery failed (%s): %s", sitemap_url, exc)
    return []


def discover_catalog(http: HttpClient, cache: HtmlCache, source: str,
                     *, refresh: bool = False, max_pages: int = 500) -> list[AnimeCard]:
    # 1. Try sitemap first (1 request gets all 300+ titles!)
    sitemap_cards = discover_sitemap(http, cache, source, refresh=refresh)
    if sitemap_cards:
        return sitemap_cards

    # 2. Fallback to paginated crawl if sitemap is missing/failed
    log.info("Falling back to paginated catalog discovery...")
    seen: dict[str, AnimeCard] = {}
    visited_urls: set[str] = set()
    url = source.rstrip("/") + "/anime/"
    pages = 0
    while url and pages < max_pages:
        if url in visited_urls:
            log.info("Cycle detected at %s; terminating pagination", url)
            break
        visited_urls.add(url)
        pages += 1
        try:
            html = fetch_cached(http, cache, url, refresh=refresh)
        except Exception as exc:
            log.warning("Listing fetch failed %s: %s", url, exc)
            break
        page = parse_listing(html, url)
        for card in page.cards:
            if card.url not in seen:
                seen[card.url] = card
        log.info("Catalog page %d: %d cards (%d unique)", pages, len(page.cards), len(seen))
        if not page.next_url or page.next_url in visited_urls:
            break
        url = page.next_url
    return list(seen.values())


def search_catalog(http: HttpClient, cache: HtmlCache, source: str, query: str,
                   *, refresh: bool = False) -> list[AnimeCard]:
    from urllib.parse import quote
    url = f"{source.rstrip('/')}/?s={quote(query)}"
    html = fetch_cached(http, cache, url, refresh=refresh)
    return parse_listing(html, url).cards
