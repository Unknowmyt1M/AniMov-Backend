"""MoviesMod Movie & Series Scraper implementation."""

import re
import urllib.parse
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup

from .config import config
from .http_client import MoviesmodHttpClient
from .models import MovieSearchResult, MovieDetail, DownloadSource
from .storage import MoviesmodStorage


class MoviesmodScraper:
    """Scraper for MoviesMod movie & series catalog."""

    def __init__(self, http_client: Optional[MoviesmodHttpClient] = None, storage: Optional[MoviesmodStorage] = None):
        self.http = http_client or MoviesmodHttpClient()
        self.storage = storage or MoviesmodStorage()

    def search(self, query: str, use_cache: bool = True) -> List[MovieSearchResult]:
        """Search movies and series on MoviesMod."""
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

            title = a_tag.get_text(strip=True)
            if not title:
                continue

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
            for q in ["480p", "720p", "1080p", "2160p", "4K", "HDR", "BluRay", "WEB-DL", "WeB-DL"]:
                if q.lower() in title.lower():
                    qualities.append(q)

            # Languages
            languages = []
            if "dual audio" in title.lower():
                languages.append("Dual Audio")
            if "multi audio" in title.lower():
                languages.append("Multi Audio")
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
            slug = slug_or_url
            page_url = f"{config.base_url}/{slug}/"

        if use_cache:
            cached = self.storage.get_movie(slug)
            if cached is not None:
                cached_dls = cached.get("downloads", [])
                if cached_dls and (cached.get("rating") or cached.get("languages") or cached.get("genres") or cached.get("synopsis")):
                    return MovieDetail(**cached)

        resp = self.http.get(page_url)
        if resp.status_code != 200:
            # Fallback: search and resolve slug
            search_query = re.sub(r'download|\b\d+p\b|hindi|english|dual audio', ' ', slug, flags=re.I)
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
                        cached_dls = cached.get("downloads", [])
                        if cached_dls and (cached.get("rating") or cached.get("languages") or cached.get("genres") or cached.get("synopsis")):
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
                    m = re.search(r"\b(19\d{2}|20\d{2})\b", v)
                    if m and not year:
                        year = m.group(1)
                elif "rating" in k or "imdb" in k:
                    r_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:/\s*10)?", v)
                    if r_match and not rating:
                        rating = f"{r_match.group(1)}/10"
                elif "duration" in k or "time" in k:
                    duration = v

        # 2. Check paragraphs
        for p in soup.select(".entry-content p, article p"):
            p_text = p.get_text(strip=True)
            if not languages and ("audio:" in p_text.lower() or "language:" in p_text.lower()):
                clean_v = p_text.split(":", 1)[-1].replace("[", "").replace("]", "").replace("{", "").replace("}", "")
                for part in re.split(r"[,/|–-]", clean_v):
                    clean_part = part.strip()
                    if clean_part and clean_part not in languages:
                        languages.append(clean_part)
            if not genres and "genre" in p_text.lower():
                raw_g = p_text.split(":", 1)[-1]
                genres = [g.strip() for g in re.split(r"[,/|]", raw_g) if g.strip()]
            if not rating and "imdb" in p_text.lower():
                r_match = re.search(r"(\d+(?:\.\d+)?\s*/\s*10)", p_text)
                if r_match:
                    rating = r_match.group(1)
            if not synopsis and any(k in p_text.lower() for k in ["storyline", "synopsis"]):
                synopsis = p_text.split(":", 1)[-1].strip()

        # Fallback for IMDb rating from anchor
        if not rating:
            imdb_link = soup.select_one('a[href*="imdb.com/title/"]')
            if imdb_link:
                m = re.search(r"(\d+(?:\.\d+)?)\s*/\s*10", imdb_link.get_text())
                if m:
                    rating = f"{m.group(1)}/10"

        # Fallback synopsis: first substantial paragraph
        if not synopsis:
            for p in soup.select(".entry-content p"):
                t = p.get_text(strip=True)
                if len(t) > 60 and not any(k in t.lower() for k in ["download", "platform", "website", "join", "telegram", "screen"]):
                    synopsis = t
                    break

        # Downloads extraction
        downloads: List[DownloadSource] = []
        seen_urls = set()
        GATEWAY_PATTERNS = ["modpro.", "archives", "episodes", "drive", "fast", "download", "hubcloud", "linksmod"]

        for a in soup.select(".entry-content a[href], article a[href]"):
            href = a["href"].strip()
            if not href.startswith("http") or href in seen_urls:
                continue

            if "moviesmod" in href or any(skip in href.lower() for skip in ["/category/", "/movies-by-", "/page/", "/tag/", "how-to", "telegram", "facebook", "twitter", "#respond"]):
                continue

            if any(k in href.lower() for k in GATEWAY_PATTERNS):
                seen_urls.add(href)
                btn_text = a.get_text(strip=True)

                parent_p = a.find_parent("p")
                prev_heading = a.find_previous(["h4", "h3", "h5", "p"])
                if prev_heading == parent_p:
                    prev_heading = prev_heading.find_previous(["h4", "h3", "h5", "p"])
                heading_txt = prev_heading.get_text(strip=True) if prev_heading else ""
                combined_txt = f"{heading_txt} {btn_text}".strip()

                quality = "Direct"
                for q in ["2160p", "4K", "1080p", "720p", "480p"]:
                    if q.lower() in combined_txt.lower():
                        quality = q
                        break

                size_match = re.search(r"\[([\d\.]+\s*(?:MB|GB)(?:/E)?)\]|\b([\d\.]+\s*(?:MB|GB)(?:/E)?)\b", combined_txt, re.I)
                size = (size_match.group(1) or size_match.group(2)) if size_match else None

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
            genres=genres,
            synopsis=synopsis,
            downloads=downloads,
            page_url=page_url,
        )

        if use_cache and detail.title:
            self.storage.set_movie(detail.id, detail.slug, detail.model_dump())

        return detail
