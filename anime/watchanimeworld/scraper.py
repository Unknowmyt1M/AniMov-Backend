"""Production-Grade WatchAnimeWorld Scraper Implementation."""

import re
import logging
from typing import List, Optional
from pathlib import Path
from bs4 import BeautifulSoup

from .config import BASE_URL
from .http_client import WatchAnimeWorldHttpClient
from .storage import WatchAnimeWorldStorage
from .models import (
    WatchAnimeWorldSearchResult,
    WatchAnimeWorldSeriesDetail,
    WatchAnimeWorldEpisode,
    WatchAnimeWorldServer,
)

logger = logging.getLogger("watchanimeworld.scraper")


class WatchAnimeWorldScraper:
    """Independent scraper for WatchAnimeWorld (watchanimeworld.one)."""

    def __init__(self, http_client: Optional[WatchAnimeWorldHttpClient] = None, storage: Optional[WatchAnimeWorldStorage] = None):
        self.client = http_client or WatchAnimeWorldHttpClient()
        self.storage = storage or WatchAnimeWorldStorage()

    def _extract_slug(self, url_or_slug: str) -> str:
        """Normalize URL or slug."""
        cleaned = url_or_slug.strip()
        if "watchanimeworld.one" in cleaned:
            match = re.search(r'/(?:series|episode|movies)/([^/?#]+)', cleaned)
            if match:
                return match.group(1)
        return cleaned.strip("/").split("/")[-1]

    def search(self, query: str) -> List[WatchAnimeWorldSearchResult]:
        """Search anime catalog on WatchAnimeWorld."""
        url = f"{BASE_URL}/"
        params = {"s": query}

        logger.info(f"Searching WatchAnimeWorld for: '{query}'")
        res = self.client.get(url, params=params)
        if res.status_code != 200:
            logger.error(f"Search failed: HTTP {res.status_code}")
            return []

        soup = BeautifulSoup(res.text, "html.parser")
        items = soup.select(".result-item, article, .item, .animation-2")
        results: List[WatchAnimeWorldSearchResult] = []

        for it in items:
            link_tag = it.find("a", href=True)
            if not link_tag:
                continue

            href = link_tag.get("href", "")
            slug = self._extract_slug(href)

            is_movie = "/movies/" in href or "movie" in it.get("class", [])
            media_type = "Anime Movie" if is_movie else "TV Series"
            episodes = "1 Ep (Movie)" if is_movie else "Hindi Dubbed Series"
            duration = "Feature Film" if is_movie else "~24m / ep"

            img_tag = it.find("img")
            poster = None
            if img_tag:
                poster = img_tag.get("data-src") or img_tag.get("src")
                if poster and poster.startswith("//"):
                    poster = f"https:{poster}"

            title_tag = it.select_one(".title, .entry-title, h3, h2") or link_tag
            title = title_tag.get_text(strip=True) if title_tag else slug.replace("-", " ").title()

            if not any(r.slug == slug for r in results):
                results.append(
                    WatchAnimeWorldSearchResult(
                        slug=slug,
                        title=title,
                        poster=poster,
                        media_type=media_type,
                        episodes=episodes,
                        duration=duration,
                        link=href if href.startswith("http") else f"{BASE_URL}{href}",
                    )
                )

        return results

    def get_series_detail(self, slug_or_url: str, use_cache: bool = True, max_age_seconds: Optional[int] = 86400 * 7) -> Optional[WatchAnimeWorldSeriesDetail]:
        """Fetch series details, metadata, and full episode catalog."""
        slug = self._extract_slug(slug_or_url)
        if use_cache:
            cached = self.storage.get_series(slug, max_age_seconds=max_age_seconds)
            if cached and cached.episodes:
                return cached

        url = slug_or_url if slug_or_url.startswith("http") else f"{BASE_URL}/series/{slug}/"
        logger.info(f"Fetching series page: {url}")
        res = self.client.get(url)
        if res.status_code == 404 and not slug_or_url.startswith("http"):
            # Fallback to /movies/ or /movie/ for movie titles
            for alt_prefix in ["/movies/", "/movie/"]:
                alt_url = f"{BASE_URL}{alt_prefix}{slug}/"
                alt_res = self.client.get(alt_url)
                if alt_res.status_code == 200:
                    res = alt_res
                    url = alt_url
                    break

        if res.status_code != 200:
            logger.error(f"Failed to fetch series page ({url}): HTTP {res.status_code}")
            return None

        soup = BeautifulSoup(res.text, "html.parser")

        title_el = soup.select_one("h1.entry-title, .data h1, h1")
        title = title_el.get_text(strip=True) if title_el else slug.replace("-", " ").title()

        poster_el = soup.select_one(".poster img, .sheader .poster img, img[data-src*='tmdb']")
        poster = None
        if poster_el:
            poster = poster_el.get("data-src") or poster_el.get("src")
            if poster and poster.startswith("//"):
                poster = f"https:{poster}"

        synopsis_el = soup.select_one(".description, .wp-content p, .sinopsis, .entry-content p")
        synopsis = synopsis_el.get_text(strip=True) if synopsis_el else None

        genres = [
            a.get_text(strip=True)
            for a in soup.select(".sgeneros a, .genres a, a[href*='/genre/'], a[href*='/genres/']")
            if a.get_text(strip=True)
        ]
        genres = list(dict.fromkeys(genres))

        # Extract episodes
        episodes: List[WatchAnimeWorldEpisode] = []
        ep_links = soup.find_all("a", href=lambda h: h and ("/episode/" in h or "/episodes/" in h))

        seen_slugs = set()
        for a in ep_links:
            href = a.get("href", "")
            ep_slug = self._extract_slug(href)
            if not ep_slug or ep_slug in seen_slugs:
                continue
            seen_slugs.add(ep_slug)

            m = re.search(r'(\d+)x(\d+)', ep_slug)
            if m:
                s_num = int(m.group(1))
                ep_num = int(m.group(2))
            else:
                s_num = 1
                ep_num = len(episodes) + 1

            parent = a.find_parent(["article", "li", ".episodes", ".post"])
            title_el = parent.find([".entry-title", "h2", "h3"]) if parent else None
            raw_ep_title = (
                title_el.get_text(strip=True)
                if title_el and title_el.get_text(strip=True)
                else (a.get_text(strip=True) or a.get("title") or f"Episode {ep_num}")
            )
            ep_title = re.sub(r"\s*-\s*Anime\s*World\s*India.*$", "", raw_ep_title, flags=re.I)
            ep_title = re.sub(r"\s*-\s*WatchAnimeWorld.*$", "", ep_title, flags=re.I).strip() or f"Episode {ep_num}"

            episodes.append(
                WatchAnimeWorldEpisode(
                    slug=ep_slug,
                    season_num=s_num,
                    episode_num=ep_num,
                    title=ep_title,
                    link=href if href.startswith("http") else f"{BASE_URL}{href}",
                )
            )

        episodes.sort(key=lambda x: (x.season_num, x.episode_num))

        detail = WatchAnimeWorldSeriesDetail(
            slug=slug,
            title=title,
            poster=poster,
            synopsis=synopsis,
            genres=genres,
            total_episodes=len(episodes),
            episodes=episodes,
        )

        self.storage.save_series(detail)
        return detail

    def get_episode_streams(self, slug_or_url: str, use_cache: bool = True) -> Optional[WatchAnimeWorldEpisode]:
        """Fetch player embeds and streaming servers for an episode."""
        ep_slug = self._extract_slug(slug_or_url)
        if use_cache:
            cached = self.storage.get_episode(ep_slug)
            if cached and cached.servers:
                return cached

        url = f"{BASE_URL}/episode/{ep_slug}/"
        logger.info(f"Fetching episode page: {url}")
        res = self.client.get(url)
        if res.status_code != 200:
            logger.error(f"Failed to fetch episode page: HTTP {res.status_code}")
            return None

        soup = BeautifulSoup(res.text, "html.parser")
        m = re.search(r'(\d+)x(\d+)', ep_slug)
        s_num = int(m.group(1)) if m else 1
        ep_num = int(m.group(2)) if m else 1

        title_el = soup.select_one("h1.entry-title, .data h1, h1")
        if title_el and title_el.get_text(strip=True):
            raw_title = title_el.get_text(strip=True)
        elif soup.title:
            raw_title = soup.title.get_text(strip=True)
        else:
            raw_title = f"Episode {ep_num}"

        clean_title = re.sub(r"\s*-\s*Anime\s*World\s*India.*$", "", raw_title, flags=re.I)
        clean_title = re.sub(r"\s*-\s*WatchAnimeWorld.*$", "", clean_title, flags=re.I).strip()
        title = clean_title or f"Episode {ep_num}"

        servers: List[WatchAnimeWorldServer] = []

        # Find iframes
        for ifr in soup.find_all("iframe", src=True):
            src = ifr.get("src", "").strip()
            if src and not any(k in src for k in ["google", "facebook", "twitter"]):
                if src.startswith("//"):
                    src = f"https:{src}"
                elif src.startswith("/"):
                    src = f"{BASE_URL}{src}"
                name = "Zephyrix" if "zephyrix" in src else "Default"
                servers.append(WatchAnimeWorldServer(name=name, embed_url=src))

        # Check server options buttons/tabs
        for opt in soup.select(".dooplay_player_option, [data-nume]"):
            s_name = opt.get_text(strip=True) or f"Server {len(servers) + 1}"
            # Some dooplay themes store embed or ajax id
            post_id = opt.get("data-post")
            nume = opt.get("data-nume")
            if post_id and nume:
                pass

        ep = WatchAnimeWorldEpisode(
            slug=ep_slug,
            season_num=s_num,
            episode_num=ep_num,
            title=title,
            link=url,
            servers=servers,
        )

        series_slug = ep_slug.rsplit("-", 1)[0]
        self.storage.save_episode(series_slug, ep)
        return ep

    def crawl_series(self, slug_or_url: str, max_episodes: Optional[int] = None) -> Optional[WatchAnimeWorldSeriesDetail]:
        """Crawl series and pre-cache episode servers."""
        detail = self.get_series_detail(slug_or_url)
        if not detail or not detail.episodes:
            return detail

        target_episodes = detail.episodes[:max_episodes] if max_episodes else detail.episodes
        logger.info(f"Crawling {len(target_episodes)} episodes for '{detail.title}'...")

        for ep in target_episodes:
            stream_ep = self.get_episode_streams(ep.slug)
            if stream_ep:
                ep.servers = stream_ep.servers

        return detail

    def close(self):
        """Close HTTP client session."""
        self.client.close()
