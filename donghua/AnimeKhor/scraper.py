"""
High-level scraper engine for AnimeKhor.
Orchestrates metadata extraction, search, episode parsing, and persistence.
"""
import re
from typing import List, Optional
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

from .config import PRIMARY_DOMAIN, SEARCH_URL, CATALOG_URL
from .http_client import HttpClient
from .models import SeriesDetail, EpisodeDetail, SearchResult
from .episode_parser import EpisodeParser
from .mirror_decoder import MirrorDecoder
from .storage import Storage


class AnimeKhorScraper:
    def __init__(self, cache_enabled: bool = True):
        self.http = HttpClient(cache_enabled=cache_enabled)
        self.storage = Storage()

    def _normalize_series_url(self, slug_or_url: str) -> str:
        if slug_or_url.startswith("http://") or slug_or_url.startswith("https://"):
            return slug_or_url
        clean_slug = slug_or_url.strip("/ ")
        return f"{PRIMARY_DOMAIN}/anime/{clean_slug}/"

    def search(self, query: str) -> List[SearchResult]:
        url = f"{SEARCH_URL}{quote_plus(query)}"
        html_content = self.http.get(url)
        soup = BeautifulSoup(html_content, "html.parser")
        results: List[SearchResult] = []
        seen_slugs = set()

        cards = soup.select(".bsx")
        for card in cards:
            a_tag = card.select_one("a")
            if not a_tag or not a_tag.get("href"):
                continue

            card_url = a_tag["href"]
            title_el = card.select_one("h2") or card.select_one(".entry-title")
            title_text = title_el.get_text(strip=True) if title_el else a_tag.get("title", "")
            if not title_text:
                tt = card.select_one(".tt")
                title_text = tt.get_text(strip=True) if tt else ""

            slug_match = re.search(r'/anime/([^/]+)/?', card_url)
            slug = slug_match.group(1) if slug_match else card_url.strip("/").split("/")[-1]

            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            type_elem = card.select_one(".typez")
            type_name = type_elem.get_text(strip=True) if type_elem else None

            ep_elem = card.select_one(".epx")
            latest_ep = ep_elem.get_text(strip=True) if ep_elem else None

            rating_elem = card.select_one(".rating")
            rating = rating_elem.get_text(strip=True) if rating_elem else None

            img_elem = card.select_one("img")
            poster = None
            if img_elem:
                for attr in ("data-lazy-src", "data-src", "data-original", "src"):
                    val = img_elem.get(attr)
                    if val and not val.startswith("data:image/svg"):
                        poster = val
                        break

            results.append(
                SearchResult(
                    title=title_text,
                    slug=slug,
                    url=card_url,
                    type_name=type_name,
                    latest_ep=latest_ep,
                    poster=poster,
                    rating=rating
                )
            )

        return results

    def get_series_detail(self, slug_or_url: str) -> SeriesDetail:
        url = self._normalize_series_url(slug_or_url)
        html_content = self.http.get(url)
        soup = BeautifulSoup(html_content, "html.parser")

        slug_match = re.search(r'/anime/([^/]+)/?', url)
        slug = slug_match.group(1) if slug_match else url.strip("/").split("/")[-1]

        title_elem = soup.select_one("h1.entry-title")
        title = title_elem.get_text(strip=True) if title_elem else slug

        native_elem = soup.select_one(".alter, span.alternative")
        native_title = native_elem.get_text(strip=True) if native_elem else None

        rating_elem = soup.select_one(".rating strong, .num")
        rating = rating_elem.get_text(strip=True) if rating_elem else None

        poster_elem = soup.select_one(".thumb img, .poster img")
        poster = None
        if poster_elem:
            for attr in ("data-lazy-src", "data-src", "data-original", "src"):
                val = poster_elem.get(attr)
                if val and not val.startswith("data:image/svg"):
                    poster = val
                    break
            if not poster and poster_elem.get("src"):
                poster = poster_elem.get("src")

        synopsis_elem = soup.select_one(".synp .entry-content, .entry-content")
        synopsis = synopsis_elem.get_text(strip=True) if synopsis_elem else None

        extra_meta = {}
        for span in soup.select(".spe span, .info-content span"):
            txt = span.get_text(strip=True)
            if ":" in txt:
                k, v = txt.split(":", 1)
                extra_meta[k.strip().lower()] = v.strip()

        status = extra_meta.get("status")
        studio = extra_meta.get("studio")
        country = extra_meta.get("country")
        released_date = extra_meta.get("released") or extra_meta.get("released on")
        duration = extra_meta.get("duration")
        season = extra_meta.get("season")
        type_name = extra_meta.get("type")

        genres = [g.get_text(strip=True) for g in soup.select(".genxed a, .genres a")]
        episodes = EpisodeParser.parse_episode_list(soup)

        series_detail = SeriesDetail(
            slug=slug,
            url=url,
            title=title,
            native_title=native_title,
            rating=rating,
            status=status,
            studio=studio,
            country=country,
            released_date=released_date,
            duration=duration,
            season=season,
            type_name=type_name,
            genres=genres,
            synopsis=synopsis,
            poster=poster,
            episodes=episodes,
            extra_meta=extra_meta
        )

        self.storage.save_series(series_detail)
        return series_detail

    def get_episode_detail(self, episode_url: str) -> EpisodeDetail:
        html_content = self.http.get(episode_url)
        soup = BeautifulSoup(html_content, "html.parser")

        title_elem = soup.select_one("h1.entry-title")
        title = title_elem.get_text(strip=True) if title_elem else "Episode"

        ep_num = EpisodeParser.extract_episode_number(title, episode_url)

        date_elem = soup.select_one("time.updated, time[datetime], .updated")
        release_date = date_elem.get_text(strip=True) if date_elem else None
        if not release_date and date_elem and date_elem.get("datetime"):
            release_date = date_elem["datetime"]

        series_link = soup.select_one(".allrec a, ol.breadcrumb li:nth-child(2) a")
        series_url = series_link["href"] if series_link and series_link.get("href") else None
        series_title = series_link.get_text(strip=True) if series_link else None

        prev_a = soup.select_one(".naveps .nvs:first-child a[href*='episode'], .prev-episode a")
        next_a = soup.select_one(".naveps .nvs:last-child a[href*='episode'], .next-episode a")
        prev_url = prev_a["href"] if prev_a and prev_a.get("href") else None
        next_url = next_a["href"] if next_a and next_a.get("href") else None

        servers = MirrorDecoder.extract_servers(soup)
        downloads = MirrorDecoder.extract_downloads(soup)

        ep_detail = EpisodeDetail(
            episode_number=ep_num,
            title=title,
            url=episode_url,
            release_date=release_date,
            series_title=series_title,
            series_url=series_url,
            servers=servers,
            downloads=downloads,
            prev_episode=prev_url,
            next_episode=next_url
        )

        self.storage.save_episode_detail(ep_detail)
        return ep_detail

    def crawl_series(self, slug_or_url: str, max_episodes: Optional[int] = None) -> SeriesDetail:
        series = self.get_series_detail(slug_or_url)
        target_episodes = series.episodes
        if max_episodes:
            target_episodes = target_episodes[:max_episodes]

        for ep in target_episodes:
            try:
                self.get_episode_detail(ep.url)
            except Exception:
                pass

        return series
