"""KMMovies Movie & Series Scraper implementation."""

import re
import urllib.parse
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup

from .config import config
from .http_client import KmmoviesHttpClient
from .models import MovieSearchResult, MovieDetail, DownloadSource
from .storage import KmmoviesStorage


class KmmoviesScraper:
    """Scraper for KMMovies catalog."""

    def __init__(self, http_client: Optional[KmmoviesHttpClient] = None, storage: Optional[KmmoviesStorage] = None):
        self.http = http_client or KmmoviesHttpClient()
        self.storage = storage or KmmoviesStorage()

    def search(self, query: str, use_cache: bool = True) -> List[MovieSearchResult]:
        """Search movies and series on KMMovies."""
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

        items = soup.select("article, .post, .item")
        for item in items:
            a_tag = item.select_one(".entry-title a, h2 a, h3 a") or item.find("a", href=True)
            if not a_tag or not a_tag.get("href"):
                continue

            href = a_tag["href"]
            if href in seen_links:
                continue
            seen_links.add(href)

            title_el = item.select_one(".movie-title, .entry-title, h2, h3")
            raw_title = title_el.get_text(strip=True) if title_el else (a_tag.get("title") or a_tag.get_text(strip=True))
            if not raw_title:
                continue

            # Clean IMDb star and language prefix
            title = re.sub(r'^[^\w\s]*\s*(\d+(\.\d+)?\s*)?(Hindi|English|Dual Audio|Multi Audio|,|\s)+', '', raw_title, flags=re.I).strip()
            if not title:
                title = raw_title

            slug = href.rstrip("/").split("/")[-1]

            # Poster
            poster = None
            img = item.find("img")
            if img:
                poster = img.get("data-src") or img.get("src")

            # Media type
            media_type = "TV Series" if any(w in title.lower() for w in ["season", "series", "s01", "s02", "episodes"]) else "Movie"

            # Year
            year_match = re.search(r"\b(19\d{2}|20\d{2})\b", title)
            year = year_match.group(1) if year_match else None

            # Qualities
            qualities = []
            for q in ["480p", "720p", "1080p", "2160p", "4K", "HDR10", "DoVi", "REMUX", "BluRay", "WEB-DL"]:
                if q.lower() in title.lower():
                    qualities.append(q)

            # Languages
            languages = []
            if "dual audio" in title.lower():
                languages.append("Dual Audio")
            if "hindi" in title.lower():
                languages.append("Hindi")
            if "english" in title.lower():
                languages.append("English")

            results.append(
                MovieSearchResult(
                    id=slug,
                    slug=slug,
                    title=title,
                    poster=poster,
                    media_type=media_type,
                    release_year=year,
                    qualities=qualities,
                    languages=languages,
                    link=href,
                )
            )

        if use_cache and results:
            self.storage.set_search(cleaned_query, [r.model_dump() for r in results])

        return results

    def get_movie_detail(self, slug_or_url: str, use_cache: bool = True) -> Optional[MovieDetail]:
        """Fetch full details and download mirrors."""
        if slug_or_url.startswith("http://") or slug_or_url.startswith("https://"):
            page_url = slug_or_url
            slug = page_url.rstrip("/").split("/")[-1]
        else:
            slug = slug_or_url.strip("/ ")
            page_url = f"{config.base_url}/{slug}/"

        if use_cache:
            cached = self.storage.get_movie(slug)
            if cached is not None:
                return MovieDetail(**cached)

        resp = self.http.get(page_url)
        if resp.status_code != 200:
            # Fallback: search and resolve slug
            search_query = re.sub(r'movieact|movie|download|\b\d+p\b|webrip', ' ', slug, flags=re.I)
            search_query = " ".join(search_query.replace("-", " ").split()[:4])
            candidates = self.search(search_query) if search_query else []
            matched_url = None
            slug_clean = slug.lower()
            for cand in candidates:
                cand_clean = cand.slug.lower()
                if cand_clean == slug_clean or cand_clean in slug_clean or slug_clean in cand_clean:
                    matched_url = cand.link
                    break
            if not matched_url and candidates:
                matched_url = candidates[0].link

            if matched_url and matched_url != page_url:
                page_url = matched_url
                slug = page_url.rstrip("/").split("/")[-1]
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
        h1 = soup.select_one("h1.entry-title, h1")
        if h1:
            title = h1.get_text(strip=True)
        if not title and soup.title:
            title = soup.title.get_text(strip=True).split("|")[0].strip()

        # Poster
        poster = None
        img = soup.select_one(".entry-content img")
        if img:
            poster = img.get("data-src") or img.get("src")

        # Media type
        media_type = "TV Series" if any(w in title.lower() for w in ["season", "series", "s01", "episodes"]) else "Movie"

        # Year
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", title)
        year = year_match.group(1) if year_match else None

        # Text metadata
        languages: List[str] = []
        genres: List[str] = []
        synopsis: Optional[str] = None
        rating: Optional[str] = None
        duration: Optional[str] = None

        for p in soup.find_all("p"):
            p_text = p.get_text(strip=True)
            if "Audio:" in p_text or "Language:" in p_text:
                for part in re.split(r"[:,-]", p_text):
                    if any(lang in part.lower() for lang in ["hindi", "english", "tamil", "telugu", "dual", "multi"]):
                        languages.append(part.strip())
            elif "Genre:" in p_text or "Genres:" in p_text:
                raw_g = re.sub(r"Genre(s)?:\s*", "", p_text)
                genres = [g.strip() for g in raw_g.split(",") if g.strip()]
            elif "IMDb Rating:" in p_text or "Rating:" in p_text:
                r_match = re.search(r"(\d+(\.\d+)?\s*/\s*10)", p_text)
                if r_match:
                    rating = r_match.group(1)
            elif "Storyline" in p_text or "Synopsis" in p_text:
                synopsis = p_text.split(":")[-1].strip()

        # Downloads extraction
        downloads: List[DownloadSource] = []
        seen_urls = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href in seen_urls:
                continue

            if not href.startswith("http"):
                continue
            if any(skip in href for skip in ["kmmovies", "facebook.com", "twitter.com", "t.me", "whatsapp.com", "imdb.com"]):
                continue

            if any(k in href for k in ["magiclinks.lol", "drive", "download", "link", "fast"]):
                seen_urls.add(href)
                btn_text = a.get_text(strip=True)

                quality = "Direct"
                for q in ["2160p", "4K", "1080p", "720p", "480p"]:
                    if q.lower() in btn_text.lower():
                        quality = q
                        break

                # Size extraction
                size_match = re.search(r"(\d+(?:\.\d+)?\s*(?:MB|GB))", btn_text, re.I)
                size = size_match.group(1) if size_match else None

                downloads.append(
                    DownloadSource(
                        quality=quality,
                        size=size,
                        url=href,
                        label=btn_text or f"{quality} Download",
                    )
                )

        detail = MovieDetail(
            id=slug,
            slug=slug,
            title=title,
            poster=poster,
            media_type=media_type,
            release_year=year,
            duration=duration,
            rating=rating,
            languages=list(set(languages)),
            genres=genres,
            synopsis=synopsis,
            downloads=downloads,
            page_url=page_url,
        )

        if use_cache and detail.title:
            self.storage.set_movie(detail.id, detail.slug, detail.model_dump())

        return detail
