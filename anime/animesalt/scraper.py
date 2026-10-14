"""Production-Grade AnimeSalt Scraper Implementation."""

import base64
import json
import re
import logging
from typing import List, Optional
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from bs4 import BeautifulSoup

from .config import BASE_URL
from .http_client import AnimeSaltHttpClient
from .storage import AnimeSaltStorage
from .models import (
    AnimeSaltSearchResult,
    AnimeSaltSeriesDetail,
    AnimeSaltEpisode,
    AnimeSaltAudioStream,
)

logger = logging.getLogger("animesalt.scraper")


class AnimeSaltScraper:
    """Independent scraper for AnimeSalt (animesalt.cx)."""

    def __init__(self, http_client: Optional[AnimeSaltHttpClient] = None, storage: Optional[AnimeSaltStorage] = None):
        self.client = http_client or AnimeSaltHttpClient()
        self.storage = storage or AnimeSaltStorage()

    def _extract_slug(self, url_or_slug: str) -> str:
        """Normalize URL or slug."""
        cleaned = url_or_slug.strip()
        if "animesalt.cx" in cleaned:
            match = re.search(r'/(?:series|episode|movies|movie)/([^/?#]+)', cleaned)
            if match:
                return match.group(1)
        return cleaned.strip("/").split("/")[-1]

    def search(self, query: str) -> List[AnimeSaltSearchResult]:
        """Search anime catalog on AnimeSalt."""
        url = f"{BASE_URL}/"
        params = {"s": query}

        logger.info(f"Searching AnimeSalt for: '{query}'")
        res = self.client.get(url, params=params)
        if res.status_code != 200:
            logger.error(f"Search failed: HTTP {res.status_code}")
            return []

        soup = BeautifulSoup(res.text, "html.parser")
        items = soup.select("article, .post, .item, .result-item, .animation-2")
        results: List[AnimeSaltSearchResult] = []

        for it in items:
            link_tag = it.find("a", href=True)
            if not link_tag:
                continue

            href = link_tag.get("href", "")
            if not any(k in href for k in ["/series/", "/movies/", "/movie/"]):
                continue

            slug = self._extract_slug(href)

            img_tag = it.find("img")
            poster = None
            if img_tag:
                poster = img_tag.get("data-src") or img_tag.get("src")
                if poster and poster.startswith("//"):
                    poster = f"https:{poster}"

            title_tag = it.select_one(".entry-title, .title, h2, h3") or link_tag
            title = title_tag.get_text(strip=True) if title_tag else slug.replace("-", " ").title()

            is_movie = "/movies/" in href or "movie" in it.get("class", [])
            anime_type = "Anime Movie" if is_movie else "TV Series"
            episodes = "1 Ep (Movie)" if is_movie else "Multi-Lang Dubs"
            duration = "Feature Film" if is_movie else "~24m / ep"

            if not any(r.slug == slug for r in results):
                results.append(
                    AnimeSaltSearchResult(
                        slug=slug,
                        title=title,
                        poster=poster,
                        anime_type=anime_type,
                        episodes=episodes,
                        duration=duration,
                        link=href if href.startswith("http") else f"{BASE_URL}{href}",
                    )
                )

        return results

    def get_series_detail(self, slug_or_url: str, use_cache: bool = True, max_age_seconds: Optional[int] = 86400 * 7) -> Optional[AnimeSaltSeriesDetail]:
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

        synopsis_el = soup.select_one(".wp-content p, .sinopsis, .entry-content p")
        synopsis = synopsis_el.get_text(strip=True) if synopsis_el else None

        genres = [
            a.get_text(strip=True)
            for a in soup.select(".sgeneros a, .genres a, a[href*='/genre/'], a[href*='/genres/']")
            if a.get_text(strip=True)
        ]
        genres = list(dict.fromkeys(genres))

        # Extract episodes
        episodes: List[AnimeSaltEpisode] = []
        ep_links = soup.find_all("a", href=lambda h: h and "/episode/" in h)

        seen_slugs = set()
        for a in ep_links:
            href = a.get("href", "")
            ep_slug = self._extract_slug(href)
            if not ep_slug or ep_slug in seen_slugs:
                continue
            seen_slugs.add(ep_slug)

            # Extract season and episode number e.g. solo-leveling-1x2
            m = re.search(r'(\d+)x(\d+)', ep_slug)
            if m:
                s_num = int(m.group(1))
                ep_num = int(m.group(2))
            else:
                s_num = 1
                ep_num = len(episodes) + 1

            parent = a.find_parent(["article", "li", ".episodes", ".post"])
            title_el = parent.find([".entry-title", "h2", "h3"]) if parent else None
            ep_title = (
                title_el.get_text(strip=True)
                if title_el and title_el.get_text(strip=True)
                else (a.get_text(strip=True) or a.get("title") or f"Episode {ep_num}")
            )

            episodes.append(
                AnimeSaltEpisode(
                    slug=ep_slug,
                    season_num=s_num,
                    episode_num=ep_num,
                    title=ep_title,
                    link=href if href.startswith("http") else f"{BASE_URL}{href}",
                )
            )

        # Sort episodes by season then episode num
        episodes.sort(key=lambda x: (x.season_num, x.episode_num))

        detail = AnimeSaltSeriesDetail(
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

    def get_episode_streams(self, slug_or_url: str, use_cache: bool = True) -> Optional[AnimeSaltEpisode]:
        """Fetch multi-language audio streams and player embeds for an episode."""
        ep_slug = self._extract_slug(slug_or_url)
        if use_cache:
            cached = self.storage.get_episode(ep_slug)
            if cached and cached.audio_streams:
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
        page_title = soup.title.get_text(strip=True) if soup.title else ""
        if page_title:
            clean_title = re.sub(r"\s*-\s*Anime\s*Salt.*$", "", page_title, flags=re.I).strip()
            title = clean_title or (title_el.get_text(strip=True) if title_el else f"Episode {ep_num}")
        else:
            title = title_el.get_text(strip=True) if title_el else f"Episode {ep_num}"

        audio_streams: List[AnimeSaltAudioStream] = []
        iframe_url = None

        for ifr in soup.find_all("iframe", src=True):
            src = ifr.get("src", "").strip()
            if not src:
                continue

            if not iframe_url:
                iframe_url = src

            # Check if multi-lang-plyr.php
            if "multi-lang-plyr.php" in src:
                parsed = urlparse(src)
                qs = parse_qs(parsed.query)
                data_param = qs.get("data", [""])[0]
                if data_param:
                    try:
                        decoded_json = base64.b64decode(data_param).decode("utf-8")
                        langs_data = json.loads(decoded_json)
                        for item in langs_data:
                            lang = item.get("language", "Unknown")
                            link = item.get("link", "")
                            if link:
                                audio_streams.append(
                                    AnimeSaltAudioStream(
                                        language=lang,
                                        link=link,
                                    )
                                )
                    except Exception as e:
                        logger.error(f"Error decoding multi-lang player data: {e}")

            elif any(k in src for k in ["abyssplayer", "play", "embed", "cdn", "stream"]):
                audio_streams.append(
                    AnimeSaltAudioStream(
                        language="Default",
                        link=src,
                    )
                )

        ep = AnimeSaltEpisode(
            slug=ep_slug,
            season_num=s_num,
            episode_num=ep_num,
            title=title,
            link=url,
            iframe_url=iframe_url,
            audio_streams=audio_streams,
        )

        series_slug = ep_slug.rsplit("-", 1)[0]
        self.storage.save_episode(series_slug, ep)
        return ep

    def crawl_series(self, slug_or_url: str, max_episodes: Optional[int] = None) -> Optional[AnimeSaltSeriesDetail]:
        """Crawl series and pre-cache episode audio streams."""
        detail = self.get_series_detail(slug_or_url)
        if not detail or not detail.episodes:
            return detail

        target_episodes = detail.episodes[:max_episodes] if max_episodes else detail.episodes
        logger.info(f"Crawling {len(target_episodes)} episodes for '{detail.title}'...")

        for ep in target_episodes:
            stream_ep = self.get_episode_streams(ep.slug)
            if stream_ep:
                ep.audio_streams = stream_ep.audio_streams
                ep.iframe_url = stream_ep.iframe_url

        return detail

    def close(self):
        """Close HTTP client session."""
        self.client.close()
