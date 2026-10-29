"""BollyFlix Movie Scraper implementation."""

import re
import urllib.parse
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup

from .config import config
from .http_client import BollyflixHttpClient
from .models import MovieSearchResult, MovieDetail, DownloadSource
from .storage import BollyflixStorage


class BollyflixScraper:
    """Scraper for BollyFlix movie and series aggregator."""

    def __init__(self, http_client: Optional[BollyflixHttpClient] = None, storage: Optional[BollyflixStorage] = None):
        self.http = http_client or BollyflixHttpClient()
        self.storage = storage or BollyflixStorage()

    def search(self, query: str, use_cache: bool = True) -> List[MovieSearchResult]:
        """Search movies and series on BollyFlix."""
        cleaned_query = query.strip()
        if not cleaned_query:
            return []

        if use_cache:
            cached = self.storage.get_search(cleaned_query)
            if cached is not None:
                return [MovieSearchResult(**item) for item in cached]

        search_url = f"{self.http.base_url}/?s={urllib.parse.quote(cleaned_query)}"
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

            title = a_tag.get_text(strip=True)
            if not title:
                continue

            slug = href.rstrip("/").split("/")[-1]

            # Poster
            poster = None
            img = item.find("img")
            if img:
                poster = img.get("data-src") or img.get("src")

            # Media type (Movie or TV Series)
            media_type = "TV Series" if any(w in title.lower() for w in ["season", "series", "s01", "s02", "episodes"]) else "Movie"

            # Year
            year_match = re.search(r"\b(19\d{2}|20\d{2})\b", title)
            year = year_match.group(1) if year_match else None

            # Qualities
            qualities = []
            for q in ["480p", "720p", "1080p", "2160p", "4K", "HDR", "BluRay", "WEB-DL"]:
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
        """Fetch full details and download/stream links for a title."""
        if slug_or_url.startswith("http://") or slug_or_url.startswith("https://"):
            page_url = slug_or_url
            slug = page_url.rstrip("/").split("/")[-1]
        else:
            slug = slug_or_url
            page_url = f"{self.http.base_url}/{slug}/"

        if use_cache:
            cached = self.storage.get_movie(slug)
            if cached is not None:
                # Invalidate stale/corrupted cache entries that have no valid downloads or empty metadata
                cached_dls = cached.get("downloads", [])
                valid_dls = [d for d in cached_dls if "bollyflix.review" not in d.get("url", "")]
                if valid_dls and (cached.get("rating") or cached.get("languages") or cached.get("genres")):
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

        # Metadata parsing from LI elements and paragraphs
        languages: List[str] = []
        genres: List[str] = []
        subtitles: Optional[str] = None
        synopsis: Optional[str] = None
        rating: Optional[str] = None
        duration: Optional[str] = None

        # 1. Parse structured list items (li)
        for li in soup.select(".entry-content li, article li"):
            li_txt = li.get_text(strip=True)
            if ":" in li_txt:
                k, v = li_txt.split(":", 1)
                k = k.strip().lower()
                v = v.strip()
                if not v:
                    continue
                if "language" in k or "audio" in k:
                    clean_v = v.replace("[", "").replace("]", "").replace("{", "").replace("}", "")
                    for part in re.split(r"[,/|–-]", clean_v):
                        clean_part = part.strip()
                        if clean_part and clean_part not in languages:
                            languages.append(clean_part)
                elif "genre" in k:
                    genres = [g.strip() for g in re.split(r"[,/|]", v) if g.strip()]
                elif "year" in k:
                    y_m = re.search(r"\b(19\d{2}|20\d{2})\b", v)
                    if y_m:
                        year = y_m.group(1)
                elif "subtitle" in k:
                    subtitles = v
                elif "duration" in k or "runtime" in k:
                    duration = v

        # 2. Fallback to paragraph parsing
        for p in soup.find_all("p"):
            p_text = p.get_text(strip=True)
            if not languages and ("Audio:" in p_text or "Language:" in p_text):
                for part in re.split(r"[:,-]", p_text):
                    if any(lang in part.lower() for lang in ["hindi", "english", "tamil", "telugu", "dual", "multi", "korean"]):
                        languages.append(part.strip())
            elif not subtitles and "Subtitles:" in p_text:
                subtitles = p_text.split("Subtitles:")[-1].strip()
            elif not genres and ("Genre:" in p_text or "Genres:" in p_text):
                raw_g = re.sub(r"Genre(s)?:\s*", "", p_text)
                genres = [g.strip() for g in raw_g.split(",") if g.strip()]
            elif not rating and ("IMDb Rating:" in p_text or "Rating:" in p_text):
                r_match = re.search(r"(\d+(\.\d+)?\s*/\s*10)", p_text)
                if r_match:
                    rating = r_match.group(1)

        # 3. IMDb rating from badge or link
        if not rating:
            imdb_tag = soup.select_one("a[href*='imdb.com']")
            if imdb_tag:
                r_m = re.search(r"\b(\d+\.\d+)\b", imdb_tag.get_text(strip=True))
                if r_m:
                    rating = f"{r_m.group(1)}/10"

        # 4. Storyline / Synopsis
        story_h = soup.find(lambda t: t.name in ["h2", "h3", "h4"] and any(s in t.get_text(strip=True).lower() for s in ["storyline", "synopsis", "about"]))
        if story_h:
            next_p = story_h.find_next_sibling("p")
            if next_p:
                synopsis = next_p.get_text(strip=True)

        # Download / Stream links extraction
        downloads: List[DownloadSource] = []
        seen_urls = set()
        GATEWAY_PATTERNS = ["linksmod.", "fxlinks.", "fast-server.", "archives.", "driveleech.", "hubcloud.", "gdflix.", "dulink.", "/elinks/", "/archives/"]

        for a in soup.select(".entry-content a[href], article a[href]"):
            href = a["href"].strip()
            if not href.startswith("http") or href in seen_urls:
                continue

            # Skip junk links
            if any(skip in href.lower() for skip in ["/category/", "/movies-by-", "/page/", "/tag/", "how-to", "telegram", "whatsapp", "facebook", "twitter", "bollyflix.review"]):
                continue

            # Must match gateway pattern or view path without bollyflix domain
            is_gateway = any(k in href.lower() for k in GATEWAY_PATTERNS) or ("/view/" in href and "bollyflix" not in href.lower())
            if not is_gateway:
                continue

            seen_urls.add(href)
            btn_text = a.get_text(strip=True)

            # Find nearest preceding heading for resolution and size (skip the parent <p> of the link)
            parent_p = a.find_parent("p")
            prev_heading = a.find_previous(["h4", "h3", "h5"])
            if not prev_heading and parent_p:
                prev_heading = parent_p.find_previous_sibling(["h4", "h3", "h5", "p"])
            heading_txt = prev_heading.get_text(strip=True) if prev_heading else ""
            combined_txt = f"{heading_txt} {btn_text}".strip()

            # Quality detection
            quality = "Direct"
            for q in ["2160p", "4K", "1080p", "720p", "480p"]:
                if q.lower() in combined_txt.lower():
                    quality = q
                    break

            # Size extraction
            size_match = re.search(r"\[([\d\.]+\s*(?:MB|GB)(?:/E)?)\]|\b([\d\.]+\s*(?:MB|GB)(?:/E)?)\b", combined_txt, re.I)
            size = (size_match.group(1) or size_match.group(2)) if size_match else None

            # Label clean up
            label = heading_txt if heading_txt and "download" not in heading_txt.lower() else (btn_text or f"{quality} Download")
            if not label or label.lower() in ["download links", "download"]:
                label = f"{quality} Download" + (f" [{size}]" if size else "")
            label = re.sub(r"^(?:Download\s*|🔗\s*|🚀\s*)+", "", label).strip()

            downloads.append(
                DownloadSource(
                    quality=quality,
                    size=size,
                    url=href,
                    label=label or f"{quality} Download",
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
            subtitles=subtitles,
            genres=genres,
            synopsis=synopsis,
            downloads=downloads,
            page_url=page_url,
        )

        if detail.title:
            self.storage.set_movie(detail.id, detail.slug, detail.model_dump())

        return detail
