"""Production-Grade AnimeSalt Scraper Implementation."""

import base64
import json
import re
import logging
from typing import List, Optional
from urllib.parse import urlparse, parse_qs, unquote
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

    def _parse_episodes(
        self,
        container: BeautifulSoup,
        default_season: Optional[int] = None,
        seen_slugs: Optional[set] = None,
    ) -> List[AnimeSaltEpisode]:
        """Extract episode items from a page or AJAX fragment."""
        if seen_slugs is None:
            seen_slugs = set()

        episodes: List[AnimeSaltEpisode] = []
        ep_links = container.find_all("a", href=lambda h: h and "/episode/" in h)

        for a in ep_links:
            href = a.get("href", "")
            ep_slug = self._extract_slug(href)
            if not ep_slug or ep_slug in seen_slugs:
                continue
            seen_slugs.add(ep_slug)

            parent = a.find_parent(["article", "li", ".episodes", ".post"])

            # Extract season and episode number e.g. naruto-1x2
            m = re.search(r'(\d+)x(\d+)', ep_slug)
            if m:
                s_num = int(m.group(1))
                ep_num = int(m.group(2))
            else:
                num_el = parent.select_one(".num-epi, .ep, .num") if parent else None
                num_text = num_el.get_text(strip=True) if num_el else ""
                m_num = re.search(r'(\d+)x(\d+)', num_text)
                if m_num:
                    s_num = int(m_num.group(1))
                    ep_num = int(m_num.group(2))
                else:
                    s_num = default_season or 1
                    m_ep = re.search(r'(?:ep|episode)[^\d]*(\d+)', ep_slug, re.I)
                    ep_num = int(m_ep.group(1)) if m_ep else len(episodes) + 1

            title_el = parent.find([".entry-title", "h2", "h3"]) if parent else None
            ep_title = (
                title_el.get_text(strip=True)
                if title_el and title_el.get_text(strip=True)
                else (a.get_text(strip=True) or a.get("title") or f"Episode {ep_num}")
            )
            ep_title = re.sub(r"\s*-\s*Anime\s*Salt.*$", "", ep_title, flags=re.I).strip() or f"Episode {ep_num}"

            episodes.append(
                AnimeSaltEpisode(
                    slug=ep_slug,
                    season_num=s_num,
                    episode_num=ep_num,
                    title=ep_title,
                    link=href if href.startswith("http") else f"{BASE_URL}{href}",
                )
            )

        return episodes

    def get_series_detail(self, slug_or_url: str, use_cache: bool = True, max_age_seconds: Optional[int] = 86400 * 7) -> Optional[AnimeSaltSeriesDetail]:
        """Fetch series details, metadata, and full episode catalog across all seasons."""
        slug = self._extract_slug(slug_or_url)
        if use_cache:
            cached = self.storage.get_series(slug, max_age_seconds=max_age_seconds)
            if cached and cached.episodes and cached.total_seasons is not None and getattr(cached, "languages", None):
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

        synopsis_el = soup.select_one("#overview-text p, .description p, .description, .wp-content p, .sinopsis, .entry-content p")
        synopsis = synopsis_el.get_text(strip=True) if synopsis_el else None

        genres = [
            a.get_text(strip=True)
            for a in soup.select(".sgeneros a, .genres a, a[href*='/category/genre/'], a[href*='/genre/'], a[href*='/genres/']")
            if a.get_text(strip=True)
        ]
        genres = list(dict.fromkeys(genres))

        languages = [
            a.get_text(strip=True)
            for a in soup.select("a[href*='/category/language/'], a[href*='/language/'], .loadactor a")
            if a.get_text(strip=True)
        ]
        languages = list(dict.fromkeys(languages))

        # Extract duration & year from pills or overview
        duration = None
        year = None
        for div in soup.find_all("div"):
            if div.find("svg") and len(div.find_all("div")) == 0:
                txt = div.get_text(" ", strip=True)
                if re.search(r'\b\d+\s*min\b', txt, re.I) and not duration:
                    duration = txt
                elif re.search(r'\b(19\d\d|20\d\d)\b', txt) and not year:
                    year = re.search(r'\b(19\d\d|20\d\d)\b', txt).group(1)

        if not duration:
            dur_el = soup.select_one(".duration .overviewCss, .duration, .runtime")
            duration = dur_el.get_text(strip=True) if dur_el else None

        if not year:
            yr_el = soup.select_one(".year .overviewCss, .year, .release-date")
            year = yr_el.get_text(strip=True) if yr_el else None

        seen_slugs = set()

        # Check for active season rendered in initial HTML
        active_season: Optional[int] = None
        active_dt = soup.select_one(".choose-season dt.n_s, .choose-season button dt")
        if active_dt and active_dt.get_text(strip=True).isdigit():
            active_season = int(active_dt.get_text(strip=True))

        episodes: List[AnimeSaltEpisode] = self._parse_episodes(
            soup, default_season=active_season, seen_slugs=seen_slugs
        )

        # Check for multiple seasons (ToroFilm AJAX choose-season selector)
        season_elements = soup.select(".choose-season a[data-season], .sel-temp a[data-season], a[data-season]")
        season_map: dict[int, str] = {}
        for el in season_elements:
            s_attr = el.get("data-season")
            p_attr = el.get("data-post")
            if s_attr and s_attr.isdigit() and p_attr:
                season_map[int(s_attr)] = p_attr

        if season_map:
            for s_num in sorted(season_map.keys()):
                # Skip if already fully extracted from initial page HTML
                if active_season and s_num == active_season and any(ep.season_num == s_num for ep in episodes):
                    continue

                post_id = season_map[s_num]
                logger.info(f"Fetching Season {s_num} episodes via AJAX for '{slug}' (post={post_id})...")
                try:
                    ajax_res = self.client.get(
                        f"{BASE_URL}/wp-admin/admin-ajax.php",
                        params={
                            "action": "action_select_season",
                            "season": str(s_num),
                            "post": str(post_id),
                        },
                    )
                    if ajax_res.status_code == 200 and ajax_res.text:
                        s_soup = BeautifulSoup(ajax_res.text, "html.parser")
                        s_eps = self._parse_episodes(
                            s_soup, default_season=s_num, seen_slugs=seen_slugs
                        )
                        episodes.extend(s_eps)
                except Exception as e:
                    logger.warning(f"Failed to fetch Season {s_num} episodes for '{slug}': {e}")

        episodes.sort(key=lambda x: (x.season_num, x.episode_num))

        detected_seasons = sorted(list(set(ep.season_num for ep in episodes))) if episodes else (sorted(season_map.keys()) if season_map else [1])
        total_seasons = len(detected_seasons)

        detail = AnimeSaltSeriesDetail(
            slug=slug,
            title=title,
            poster=poster,
            synopsis=synopsis,
            genres=genres,
            languages=languages,
            duration=duration,
            year=year,
            total_episodes=len(episodes),
            total_seasons=total_seasons,
            seasons=detected_seasons,
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

        for ifr in soup.find_all("iframe"):
            src = ifr.get("src") or ifr.get("data-src") or ""
            src = src.strip()
            if not src:
                continue

            if not iframe_url and not any(k in src.lower() for k in ["google", "facebook", "twitter"]):
                iframe_url = src

            # Decode JSON multi-language tracks from player.php?data= or multi-lang-plyr.php?data=
            if "data=" in src:
                parsed = urlparse(src)
                qs = parse_qs(parsed.query)
                data_param = qs.get("data", [""])[0]
                if data_param:
                    try:
                        decoded_json = base64.b64decode(unquote(data_param)).decode("utf-8")
                        langs_data = json.loads(decoded_json)
                        for item in langs_data:
                            lang = item.get("language", "Unknown")
                            link = item.get("link", "")
                            if link and not any(s.link == link for s in audio_streams):
                                audio_streams.append(
                                    AnimeSaltAudioStream(
                                        language=lang,
                                        link=link,
                                    )
                                )
                    except Exception as e:
                        logger.error(f"Error decoding multi-lang player data: {e}")

            elif any(k in src.lower() for k in ["abyssplayer", "ravok", "zephyrix", "play", "embed", "cdn", "stream"]):
                if not any(s.link == src for s in audio_streams):
                    name = "Ravok" if "ravok" in src.lower() else ("Zephyrix" if "zephyrix" in src.lower() else "Default")
                    audio_streams.append(
                        AnimeSaltAudioStream(
                            language=name,
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
