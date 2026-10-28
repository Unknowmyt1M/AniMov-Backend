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

    def _parse_episodes(
        self,
        container: BeautifulSoup,
        default_season: Optional[int] = None,
        seen_slugs: Optional[set] = None,
    ) -> List[WatchAnimeWorldEpisode]:
        """Extract episode items from a page or AJAX fragment."""
        if seen_slugs is None:
            seen_slugs = set()

        episodes: List[WatchAnimeWorldEpisode] = []
        ep_links = container.find_all("a", href=lambda h: h and ("/episode/" in h or "/episodes/" in h))

        for a in ep_links:
            href = a.get("href", "")
            ep_slug = self._extract_slug(href)
            if not ep_slug or ep_slug in seen_slugs:
                continue
            seen_slugs.add(ep_slug)

            parent = a.find_parent(["article", "li", ".episodes", ".post"])

            # Detect season and episode numbers
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

        return episodes

    def get_series_detail(self, slug_or_url: str, use_cache: bool = True, max_age_seconds: Optional[int] = 86400 * 7) -> Optional[WatchAnimeWorldSeriesDetail]:
        """Fetch series details, metadata, and full episode catalog across all seasons."""
        slug = self._extract_slug(slug_or_url)
        if use_cache:
            cached = self.storage.get_series(slug, max_age_seconds=max_age_seconds)
            # Re-fetch if cached series is from older scraper version missing total_seasons or languages
            if cached and cached.episodes and cached.total_seasons is not None and getattr(cached, "languages", None):
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

        synopsis_el = soup.select_one(".description p, .description, .wp-content p, .sinopsis, .entry-content p")
        synopsis = synopsis_el.get_text(strip=True) if synopsis_el else None

        genres = [
            a.get_text(strip=True)
            for a in soup.select(".sgeneros a, .genres a, a[href*='/category/genre/'], a[href*='/genre/']")
            if a.get_text(strip=True)
        ]
        genres = list(dict.fromkeys(genres))

        languages = [
            a.get_text(strip=True)
            for a in soup.select("a[href*='/category/language/'], a[href*='/language/'], .loadactor a")
            if a.get_text(strip=True)
        ]
        languages = list(dict.fromkeys(languages))

        duration_el = soup.select_one(".duration .overviewCss, .duration, .runtime")
        duration = duration_el.get_text(strip=True) if duration_el else None

        year_el = soup.select_one(".year .overviewCss, .year, .release-date")
        year = year_el.get_text(strip=True) if year_el else None

        seen_slugs = set()

        # Check for active season rendered in initial HTML
        active_season: Optional[int] = None
        active_dt = soup.select_one(".choose-season dt.n_s")
        if active_dt and active_dt.get_text(strip=True).isdigit():
            active_season = int(active_dt.get_text(strip=True))

        episodes: List[WatchAnimeWorldEpisode] = self._parse_episodes(
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

        detail = WatchAnimeWorldSeriesDetail(
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

        # Detect audio type (e.g. Multi-Audio, Hindi Dubbed)
        audio_el = soup.select_one(".rtg.active, .rtg, .lang-select, .server-lang")
        audio_type = audio_el.get_text(strip=True) if audio_el else None

        servers: List[WatchAnimeWorldServer] = []
        seen_embeds = set()

        # Check server tab buttons and matching divs (e.g. #options-0, #options-1)
        server_buttons = soup.select(".optl a[href^='#options-'], a[href^='#options-']")
        if server_buttons:
            for btn in server_buttons:
                target_id = btn.get("href", "").lstrip("#")
                srv_name_el = btn.select_one(".server")
                srv_name = srv_name_el.get_text(strip=True) if srv_name_el else btn.get_text(" ", strip=True)

                target_div = soup.find(id=target_id)
                if target_div:
                    ifr = target_div.find("iframe")
                    if ifr:
                        src = ifr.get("src") or ifr.get("data-src") or ""
                        src = src.strip()
                        if src and src not in seen_embeds:
                            seen_embeds.add(src)
                            if src.startswith("//"):
                                src = f"https:{src}"
                            elif src.startswith("/"):
                                src = f"{BASE_URL}{src}"
                            servers.append(WatchAnimeWorldServer(name=srv_name or f"Server {len(servers)+1}", embed_url=src))

        # Fallback: scan any remaining iframes not yet captured
        for ifr in soup.find_all("iframe"):
            src = ifr.get("src") or ifr.get("data-src") or ""
            src = src.strip()
            if src and src not in seen_embeds and not any(k in src.lower() for k in ["google", "facebook", "twitter", "ads"]):
                seen_embeds.add(src)
                if src.startswith("//"):
                    src = f"https:{src}"
                elif src.startswith("/"):
                    src = f"{BASE_URL}{src}"
                name = "Zephyrix" if "zephyrix" in src else f"Server {len(servers) + 1}"
                servers.append(WatchAnimeWorldServer(name=name, embed_url=src))

        ep = WatchAnimeWorldEpisode(
            slug=ep_slug,
            season_num=s_num,
            episode_num=ep_num,
            title=title,
            link=url,
            audio_type=audio_type,
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
