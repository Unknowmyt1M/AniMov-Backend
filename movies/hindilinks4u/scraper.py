"""Hindilinks4u Movie Scraper implementation."""

import re
import urllib.parse
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup

from .config import config
from .http_client import Hindilinks4uHttpClient
from .models import MovieSearchResult, MovieDetail, StreamSource
from .storage import Hindilinks4uStorage


class Hindilinks4uScraper:
    """Scraper for Hindilinks4u movie portal."""

    def __init__(self, http_client: Optional[Hindilinks4uHttpClient] = None, storage: Optional[Hindilinks4uStorage] = None):
        self.http = http_client or Hindilinks4uHttpClient()
        self.storage = storage or Hindilinks4uStorage()

    def search(self, query: str, use_cache: bool = True) -> List[MovieSearchResult]:
        """Search movies on Hindilinks4u."""
        cleaned_query = query.strip()
        if not cleaned_query:
            return []

        if use_cache:
            cached = self.storage.get_search(cleaned_query)
            if cached is not None:
                return [MovieSearchResult(**item) for item in cached]

        search_url = f"{config.base_url}/?s={urllib.parse.quote(cleaned_query)}"
        resp = self.http.get(search_url)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results: List[MovieSearchResult] = []
        seen_links = set()

        # Target movie cards or search result links
        items = soup.select(".movie-item, .item, article, .post")
        if not items:
            # Fallback: search for movie link anchors
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if ("full-movie" in href or "/movie/" in href) and href not in seen_links:
                    seen_links.add(href)
                    title = a.get_text(strip=True)
                    if not title or len(title) < 2:
                        img = a.find("img")
                        if img and img.get("alt"):
                            title = img["alt"]
                        elif img and img.get("title"):
                            title = img["title"]
                    if title:
                        slug = href.rstrip("/").split("/")[-1]
                        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", title)
                        year = year_match.group(1) if year_match else None
                        results.append(
                            MovieSearchResult(
                                id=slug,
                                slug=slug,
                                title=title,
                                release_year=year,
                                media_type="Movie",
                                link=href,
                            )
                        )
        else:
            for item in items:
                a_tag = item.find("a", href=True)
                if not a_tag:
                    continue
                href = a_tag["href"]
                if href in seen_links:
                    continue
                seen_links.add(href)

                # Title
                title_tag = item.select_one(".title, .entry-title, h2, h3") or a_tag
                raw_title = title_tag.get_text(strip=True) if title_tag else ""
                if not raw_title:
                    img = item.find("img")
                    if img:
                        raw_title = img.get("alt") or img.get("title") or ""
                if not raw_title:
                    continue

                slug = href.rstrip("/").split("/")[-1]
                # Poster
                poster = None
                img = item.find("img")
                if img:
                    poster = img.get("data-src") or img.get("src")

                # Year, Quality, Score
                year_match = re.search(r"\b(19\d{2}|20\d{2})\b", raw_title)
                year = year_match.group(1) if year_match else None

                quality = None
                qual_tag = item.select_one(".quality, .hd, .badge")
                if qual_tag:
                    quality = qual_tag.get_text(strip=True)
                elif "1080p" in raw_title:
                    quality = "1080p"
                elif "720p" in raw_title:
                    quality = "720p"

                score = None
                score_tag = item.select_one(".rating, .imdb, .score")
                if score_tag:
                    score = score_tag.get_text(strip=True)

                results.append(
                    MovieSearchResult(
                        id=slug,
                        slug=slug,
                        title=raw_title,
                        poster=poster,
                        media_type="Movie",
                        release_year=year,
                        quality=quality,
                        score=score,
                        link=href,
                    )
                )

        if use_cache and results:
            self.storage.set_search(cleaned_query, [r.model_dump() for r in results])

        return results

    def get_movie_detail(self, slug_or_url: str, use_cache: bool = True) -> Optional[MovieDetail]:
        """Fetch comprehensive details and streams for a movie."""
        if slug_or_url.startswith("http://") or slug_or_url.startswith("https://"):
            page_url = slug_or_url
            slug = page_url.rstrip("/").split("/")[-1]
        else:
            slug = slug_or_url
            page_url = f"{config.base_url}/{slug}/"

        if use_cache:
            cached = self.storage.get_movie(slug)
            if cached is not None:
                return MovieDetail(**cached)

        resp = self.http.get(page_url)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Title
        title = ""
        h3_tag = soup.find("h3")
        if h3_tag and h3_tag.get_text(strip=True):
            title = h3_tag.get_text(strip=True)
        if not title:
            h1_tag = soup.find("h1")
            if h1_tag and h1_tag.get_text(strip=True) and "404" not in h1_tag.get_text():
                title = h1_tag.get_text(strip=True)
        if not title and soup.title:
            title = soup.title.get_text(strip=True).split("-")[0].strip()

        # Poster
        poster = None
        img_tag = soup.select_one(".poster img, .entry-content img, article img")
        if img_tag:
            poster = img_tag.get("data-src") or img_tag.get("src")
        if not poster:
            meta_og = soup.find("meta", property="og:image")
            if meta_og and meta_og.get("content"):
                poster = meta_og["content"]

        # Parse text metadata (genres, director, cast, country, year)
        genres: List[str] = []
        directors: List[str] = []
        cast: List[str] = []
        country = None
        year = None
        synopsis = None

        text_content = resp.text
        for p in soup.find_all("p"):
            p_text = p.get_text(strip=True)
            if p_text.startswith("Genre:"):
                raw_genres = p_text.replace("Genre:", "").strip()
                genres = [g.strip() for g in raw_genres.split(",") if g.strip()]
            elif p_text.startswith("Director:"):
                raw_dirs = p_text.replace("Director:", "").strip()
                directors = [d.strip() for d in raw_dirs.split(",") if d.strip()]
            elif p_text.startswith("Actors:"):
                raw_cast = p_text.replace("Actors:", "").strip()
                cast = [c.strip() for c in raw_cast.split(",") if c.strip()]
            elif p_text.startswith("Country:"):
                country = p_text.replace("Country:", "").strip()
            elif not synopsis and len(p_text) > 40 and not any(p_text.startswith(k) for k in ["Genre:", "Director:", "Actors:", "Country:", "Year:"]):
                synopsis = p_text

        # Year from title if not found
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", title)
        if year_match:
            year = year_match.group(1)

        # Streams extraction
        streams: List[StreamSource] = []
        trailer_url = None

        # Look for iframe tags
        for iframe in soup.find_all("iframe"):
            src = iframe.get("src")
            if not src:
                continue
            if src.startswith("//"):
                src = "https:" + src
            if "youtube.com" in src or "youtu.be" in src:
                trailer_url = src
            else:
                server_name = "Player"
                if "speedostream" in src:
                    server_name = "SpeedoStream"
                elif "playhub" in src:
                    server_name = "PlayHub"
                elif "dood" in src:
                    server_name = "DoodStream"
                elif "streamtape" in src:
                    server_name = "Streamtape"
                streams.append(
                    StreamSource(
                        server_name=server_name,
                        embed_url=src,
                        source_type="iframe",
                        headers={"Referer": config.base_url + "/"},
                    )
                )

        detail = MovieDetail(
            id=slug,
            slug=slug,
            title=title,
            poster=poster,
            media_type="Movie",
            release_year=year,
            genres=genres,
            synopsis=synopsis,
            directors=directors,
            cast=cast,
            country=country,
            streams=streams,
            trailer_url=trailer_url,
            page_url=page_url,
        )

        if use_cache and detail.title:
            self.storage.set_movie(detail.id, detail.slug, detail.model_dump())

        return detail
