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
            if raw_type == "tv":
                link = f"{config.base_url}/watch/tv/{tmdb_id}"
            else:
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

    def get_movie_detail(
        self,
        tmdb_id_or_url: str,
        media_type: Optional[str] = None,
        use_cache: bool = True,
    ) -> Optional[MovieDetail]:
        """Fetch full details and streaming sources for a title."""
        raw_input = str(tmdb_id_or_url).strip()
        resolved_type: Optional[str] = None

        if "/" in raw_input:
            parts = [p for p in raw_input.rstrip("/").split("/") if p]
            tmdb_id = parts[-1]
            if "tv" in parts:
                resolved_type = "tv"
            elif "movie" in parts:
                resolved_type = "movie"
        else:
            tmdb_id = raw_input

        if media_type:
            norm_type = media_type.strip().lower()
            if norm_type in ("tv", "tv series", "series"):
                resolved_type = "tv"
            elif norm_type in ("movie", "movies"):
                resolved_type = "movie"
            else:
                raise ValueError(
                    f"Unsupported media_type '{media_type}'. Must be 'movie' or 'tv'."
                )

        if not resolved_type:
            raise ValueError(
                f"Ambiguous TMDB ID '{tmdb_id}': Media type ('movie' or 'tv') must be specified "
                f"because numeric TMDB IDs for Movies and TV Series overlap. "
                f"Please provide media_type='movie' or media_type='tv', or use a full URL with '/tv/' or '/movie/'."
            )

        cache_id = f"{resolved_type}:{tmdb_id}"
        if use_cache:
            cached = self.storage.get_movie(cache_id)
            if cached is not None:
                return MovieDetail(**cached)

        # 1. Fetch metadata from /api/details/{id} or /api/details/{id}?type=tv
        if resolved_type == "tv":
            details_url = f"{config.base_url}/api/details/{tmdb_id}?type=tv"
        else:
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
        display_media_type = "TV Series" if resolved_type == "tv" else "Movie"

        release_date = data.get("release_date") or data.get("first_air_date") or ""
        year = release_date.split("-")[0] if release_date else None

        if resolved_type == "tv":
            num_seasons = data.get("number_of_seasons")
            num_eps = data.get("number_of_episodes")
            if num_seasons:
                duration = f"{num_seasons} Season{'s' if num_seasons != 1 else ''} ({num_eps or 0} Ep{'s' if num_eps != 1 else ''})"
            else:
                duration = None
        else:
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

        if resolved_type == "tv":
            watch_url = f"{config.base_url}/watch/tv/{tmdb_id}"
        else:
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

        # Add universal provider mirrors
        if resolved_type == "movie":
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
        elif resolved_type == "tv":
            streams.append(
                StreamSource(
                    server_name="VidSrc",
                    embed_url=f"https://vidsrc.to/embed/tv/{tmdb_id}",
                    source_type="iframe",
                    headers={"Referer": "https://vidsrc.to"},
                )
            )
            streams.append(
                StreamSource(
                    server_name="2Embed",
                    embed_url=f"https://www.2embed.cc/embedtv/{tmdb_id}&s=1&e=1",
                    source_type="iframe",
                    headers={"Referer": "https://www.2embed.cc"},
                )
            )
            streams.append(
                StreamSource(
                    server_name="AutoEmbed",
                    embed_url=f"https://player.autoembed.cc/embed/tv/{tmdb_id}/1/1",
                    source_type="iframe",
                    headers={"Referer": "https://autoembed.cc"},
                )
            )

        detail = MovieDetail(
            id=tmdb_id,
            title=title,
            original_title=original_title,
            media_type=display_media_type,
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
            self.storage.set_movie(cache_id, detail.model_dump())

        return detail

    def get_tv_season(self, tmdb_id: str, season_number: int = 1) -> Optional[Dict[str, Any]]:
        """Fetch TV season details and episode list from /api/tv/{id}/season/{season_number}."""
        url = f"{config.base_url}/api/tv/{tmdb_id}/season/{season_number}"
        resp = self.http.get(url)
        if resp.status_code != 200:
            return None
        try:
            return resp.json()
        except Exception:
            return None
