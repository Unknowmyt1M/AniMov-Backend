"""1Tube Movie & TV Scraper implementation."""

import re
import urllib.parse
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup

from .config import config
from .http_client import OneTubeHttpClient
from .models import MovieSearchResult, MovieDetail, StreamSource
from .storage import OneTubeStorage


class OneTubeScraper:
    """Scraper for 1Tube API-backed streaming platform."""

    def __init__(self, http_client: Optional[OneTubeHttpClient] = None, storage: Optional[OneTubeStorage] = None):
        self.http = http_client or OneTubeHttpClient()
        self.storage = storage or OneTubeStorage()

    def search(self, query: str, use_cache: bool = True) -> List[MovieSearchResult]:
        """Search movies and TV shows via 1Tube API."""
        cleaned_query = query.strip()
        if not cleaned_query:
            return []

        if use_cache:
            cached = self.storage.get_search(cleaned_query)
            if cached is not None:
                return [MovieSearchResult(**item) for item in cached]

        search_url = f"{config.base_url}/api/search?query={urllib.parse.quote(cleaned_query)}"
        resp = self.http.get(search_url)
        if resp.status_code != 200:
            return []

        try:
            data = resp.json()
        except Exception:
            return []

        results: List[MovieSearchResult] = []
        raw_items = data.get("results", []) if isinstance(data, dict) else []

        for item in raw_items:
            tmdb_id = str(item.get("id", ""))
            if not tmdb_id:
                continue

            title = item.get("title") or item.get("name") or "Untitled"
            raw_type = item.get("media_type", "movie")
            media_type = "TV Series" if raw_type == "tv" else "Movie"

            release_date = item.get("release_date") or item.get("first_air_date") or ""
            year = release_date.split("-")[0] if release_date else None

            poster_path = item.get("poster_path")
            poster = f"{config.tmdb_image_base}{poster_path}" if poster_path else None

            vote = item.get("vote_average")
            score = f"{vote:.1f}/10" if vote is not None else None

            overview = item.get("overview")
            link = f"{config.base_url}/watch/{tmdb_id}"

            results.append(
                MovieSearchResult(
                    id=tmdb_id,
                    title=title,
                    media_type=media_type,
                    release_year=year,
                    poster=poster,
                    score=score,
                    overview=overview,
                    link=link,
                )
            )

        if use_cache and results:
            self.storage.set_search(cleaned_query, [r.model_dump() for r in results])

        return results

    def get_movie_detail(self, tmdb_id_or_url: str, use_cache: bool = True) -> Optional[MovieDetail]:
        """Fetch full details and streaming sources for a title."""
        if "/" in tmdb_id_or_url:
            tmdb_id = tmdb_id_or_url.rstrip("/").split("/")[-1]
        else:
            tmdb_id = tmdb_id_or_url

        if use_cache:
            cached = self.storage.get_movie(tmdb_id)
            if cached is not None:
                return MovieDetail(**cached)

        # 1. Fetch metadata from /api/details/{id}
        details_url = f"{config.base_url}/api/details/{tmdb_id}"
        resp = self.http.get(details_url)
        if resp.status_code != 200:
            return None

        try:
            data = resp.json()
        except Exception:
            return None

        title = data.get("title") or data.get("name") or "Untitled"
        original_title = data.get("original_title") or data.get("original_name")
        raw_type = data.get("media_type", "movie")
        media_type = "TV Series" if raw_type == "tv" or "number_of_seasons" in data else "Movie"

        release_date = data.get("release_date") or data.get("first_air_date") or ""
        year = release_date.split("-")[0] if release_date else None

        runtime = data.get("runtime")
        duration = f"{runtime} min" if runtime else None

        vote_avg = data.get("vote_average")
        rating = f"{vote_avg:.1f}/10" if vote_avg is not None else None
        vote_count = data.get("vote_count")

        genres = [g.get("name") for g in data.get("genres", []) if isinstance(g, dict) and g.get("name")]
        synopsis = data.get("overview")
        tagline = data.get("tagline")

        poster_path = data.get("poster_path")
        poster = f"{config.tmdb_image_base}{poster_path}" if poster_path else None

        backdrop_path = data.get("backdrop_path")
        backdrop = f"{config.tmdb_image_base}{backdrop_path}" if backdrop_path else None

        watch_url = f"{config.base_url}/watch/{tmdb_id}"

        # 2. Extract streams from watch page and embed providers
        streams: List[StreamSource] = []

        try:
            watch_resp = self.http.get(watch_url)
            if watch_resp.status_code == 200:
                soup = BeautifulSoup(watch_resp.text, "html.parser")
                # Check for iframes
                for ifr in soup.find_all("iframe"):
                    src = ifr.get("src")
                    if src and src.startswith("http"):
                        streams.append(
                            StreamSource(
                                server_name="1Tube Player",
                                embed_url=src,
                                source_type="iframe",
                                headers={"Referer": watch_url},
                            )
                        )
                # Check for layla embed scripts
                layla_matches = re.findall(r'https?://[^\s"\'`<>]*layla[^\s"\'`<>]*', watch_resp.text)
                for layla_url in set(layla_matches):
                    streams.append(
                        StreamSource(
                            server_name="Layla Embed",
                            embed_url=layla_url,
                            source_type="script",
                            headers={"Referer": watch_url},
                        )
                    )
        except Exception:
            pass

        # Add robust universal provider mirrors
        if media_type == "Movie":
            streams.append(
                StreamSource(
                    server_name="VidSrc",
                    embed_url=f"https://vidsrc.to/embed/movie/{tmdb_id}",
                    source_type="iframe",
                    headers={"Referer": "https://vidsrc.to"},
                )
            )
            streams.append(
                StreamSource(
                    server_name="2Embed",
                    embed_url=f"https://www.2embed.cc/embed/{tmdb_id}",
                    source_type="iframe",
                    headers={"Referer": "https://www.2embed.cc"},
                )
            )
            streams.append(
                StreamSource(
                    server_name="AutoEmbed",
                    embed_url=f"https://player.autoembed.cc/embed/movie/{tmdb_id}",
                    source_type="iframe",
                    headers={"Referer": "https://autoembed.cc"},
                )
            )

        detail = MovieDetail(
            id=tmdb_id,
            title=title,
            original_title=original_title,
            media_type=media_type,
            release_year=year,
            duration=duration,
            rating=rating,
            vote_count=vote_count,
            genres=genres,
            synopsis=synopsis,
            tagline=tagline,
            poster=poster,
            backdrop=backdrop,
            streams=streams,
            watch_url=watch_url,
        )

        if use_cache and detail.title:
            self.storage.set_movie(detail.id, detail.model_dump())

        return detail
