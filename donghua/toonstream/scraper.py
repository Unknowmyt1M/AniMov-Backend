"""Core Scraper for Toonstream."""

import re
import logging
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from .http_client import ToonstreamHttpClient
from .models import (
    ToonstreamSearchResult,
    ToonstreamDetail,
    ToonstreamSeason,
    ToonstreamEpisode,
    ToonstreamStreamServer,
)

logger = logging.getLogger("toonstream.scraper")


class ToonstreamScraper:
    """Scraper implementation for Toonstream (Cartoons, Donghua, Anime, Movies)."""

    def __init__(self, http_client: Optional[ToonstreamHttpClient] = None):
        self.http = http_client or ToonstreamHttpClient()

    def _clean_title(self, raw_title: str) -> str:
        """Strip redundant suffix words."""
        cleaned = re.sub(r"(?i)\s*Watch Online\s*", "", raw_title)
        return cleaned.strip()

    def _identify_server_name(self, url: str) -> str:
        """Derive friendly server name from embed URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if "rubystm" in domain or "streamruby" in domain:
            return "RubyStream"
        if "filesforever" in domain:
            return "FilesForever"
        if "cloudy" in domain or "upns" in domain:
            return "Cloudy"
        if "vidmoly" in domain:
            return "VidMoly"
        if "abyss" in domain:
            return "AbyssPlayer"
        if "ravok" in domain:
            return "Ravok"
        if "turbo" in domain:
            return "TurboVid"
        if "youtube" in domain or "youtu.be" in domain:
            return "YouTube Trailer"
        return domain or "StreamServer"

    def search(self, query: str, page: int = 1) -> List[ToonstreamSearchResult]:
        """Search items across Toonstream catalog."""
        path = f"/s?q={query}&type=all&page={page}"
        resp = self.http.get(path)
        soup = BeautifulSoup(resp.text, "html.parser")

        results: List[ToonstreamSearchResult] = []
        for item in soup.select("#movies-a > ul > li"):
            title_el = item.select_one("article > header > h2")
            link_el = item.select_one("article > a")
            img_el = item.select_one("article figure img, article img")
            vote_el = item.select_one("span.vote")

            if not title_el or not link_el:
                continue

            href = link_el.get("href", "")
            title = self._clean_title(title_el.text)
            poster = img_el.get("src", "") if img_el else None
            score = vote_el.text.strip() if vote_el else None

            # Determine media type and slug
            slug = href.strip("/").split("/")[-1]
            media_type = "series" if "series" in href else "movies"

            results.append(
                ToonstreamSearchResult(
                    title=title,
                    link=href,
                    slug=slug,
                    poster=poster,
                    media_type=media_type,
                    score=score,
                )
            )
        return results

    def get_catalog(self, category: str = "series", page: int = 1) -> List[ToonstreamSearchResult]:
        """Browse catalog by category: 'series', 'category/cartoon', 'category/anime', 'category/movies'."""
        path = f"/{category.strip('/')}?type=all&page={page}"
        resp = self.http.get(path)
        soup = BeautifulSoup(resp.text, "html.parser")

        results: List[ToonstreamSearchResult] = []
        for item in soup.select("#movies-a > ul > li"):
            title_el = item.select_one("article > header > h2")
            link_el = item.select_one("article > a")
            img_el = item.select_one("article figure img, article img")
            vote_el = item.select_one("span.vote")

            if not title_el or not link_el:
                continue

            href = link_el.get("href", "")
            title = self._clean_title(title_el.text)
            poster = img_el.get("src", "") if img_el else None
            score = vote_el.text.strip() if vote_el else None

            slug = href.strip("/").split("/")[-1]
            media_type = "series" if "series" in href else "movies"

            results.append(
                ToonstreamSearchResult(
                    title=title,
                    link=href,
                    slug=slug,
                    poster=poster,
                    media_type=media_type,
                    score=score,
                )
            )
        return results

    def get_detail(self, link_or_slug: str, include_episodes: bool = True) -> ToonstreamDetail:
        """Fetch full series or movie metadata with all seasons and episodes."""
        if link_or_slug.startswith("http"):
            url = link_or_slug
        elif link_or_slug.startswith("/"):
            url = f"{self.http.base_url}{link_or_slug}"
        else:
            # Default to /series/<slug>
            url = f"{self.http.base_url}/series/{link_or_slug}"

        resp = self.http.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        title_el = soup.select_one("header.entry-header > h1, h1")
        title = self._clean_title(title_el.text) if title_el else link_or_slug

        poster_el = soup.select_one("article.post.single div.post-thumbnail img, div.post-thumbnail img")
        poster = poster_el.get("src") if poster_el else None

        bg_el = soup.select_one("div.bghd > img")
        backdrop = bg_el.get("src") if bg_el else None

        desc_el = soup.select_one("div.description > p")
        synopsis = desc_el.text.strip() if desc_el else None

        cast = [a.text.strip() for a in soup.select("p.loadactor a")]
        duration_el = soup.select_one("span.duration")
        duration = duration_el.text.strip() if duration_el else None

        genres = [a.text.strip() for a in soup.select("div.single-category a, p.genres a")]

        media_type = "series" if "series" in url else "movies"
        slug = url.strip("/").split("/")[-1]

        seasons: List[ToonstreamSeason] = []
        movie_streams: List[ToonstreamStreamServer] = []

        if media_type == "series":
            season_links = soup.select("div.season-swiper-wrapper a[data-url]")
            for i, s_link in enumerate(season_links, start=1):
                s_name = s_link.text.strip() or f"Season {i}"
                data_url = s_link.get("data-url", "")
                
                episodes = []
                if include_episodes and data_url:
                    try:
                        episodes = self.get_season_episodes(data_url, season_num=i)
                    except Exception as e:
                        logger.warning(f"Failed to fetch episodes for {data_url}: {e}")

                seasons.append(
                    ToonstreamSeason(
                        season_num=i,
                        title=s_name,
                        data_url=data_url,
                        episodes=episodes,
                    )
                )
        else:
            # For movies, extract stream options directly from page
            movie_streams = self.get_stream_servers(url)

        return ToonstreamDetail(
            title=title,
            slug=slug,
            link=url,
            media_type=media_type,
            poster=poster,
            backdrop=backdrop,
            synopsis=synopsis,
            cast=cast,
            duration=duration,
            genres=genres,
            seasons=seasons,
            movie_streams=movie_streams,
        )

    def get_season_episodes(self, season_data_url: str, season_num: int = 1) -> List[ToonstreamEpisode]:
        """Fetch episodes list for a specific season URL."""
        resp = self.http.get(season_data_url)
        soup = BeautifulSoup(resp.text, "html.parser")

        episodes: List[ToonstreamEpisode] = []
        for ep_art in soup.select("article.episodes"):
            a_el = ep_art.select_one("a.lnk-blk")
            if not a_el:
                continue

            href = a_el.get("href", "")
            code_el = ep_art.select_one(".num-epi")
            code_str = code_el.text.strip() if code_el else f"{season_num}x1"

            # Parse episode number from code like '1x12' -> 12
            ep_num = 1
            if "x" in code_str:
                try:
                    ep_num = int(code_str.split("x")[1])
                except ValueError:
                    pass

            name_el = ep_art.select_one("h2, .entry-title")
            ep_title = name_el.text.strip() if name_el and name_el.text.strip() else f"Episode {ep_num}"
            img_el = ep_art.select_one("div.post-thumbnail2 img, img")
            thumb = img_el.get("src") if img_el else None

            episodes.append(
                ToonstreamEpisode(
                    title=ep_title,
                    episode_code=code_str,
                    season_num=season_num,
                    episode_num=ep_num,
                    link=href,
                    thumbnail=thumb,
                )
            )
        return episodes

    def get_stream_servers(self, episode_or_movie_url: str) -> List[ToonstreamStreamServer]:
        """Extract all streaming iframes and resolve inner embed links."""
        resp = self.http.get(episode_or_movie_url)
        soup = BeautifulSoup(resp.text, "html.parser")

        iframe_elements = soup.select("#aa-options iframe, ul.play-options iframe, iframe")
        servers: List[ToonstreamStreamServer] = []

        for f in iframe_elements:
            raw_src = f.get("src") or f.get("data-src")
            if not raw_src:
                continue

            if raw_src.startswith("/"):
                embed_url = f"{self.http.base_url}{raw_src}"
            else:
                embed_url = raw_src

            # Check if this embed hosts an inner player iframe
            inner_url = None
            try:
                # If relative or on toonstream.vip, probe for inner player
                if self.http.base_url in embed_url or embed_url.startswith("/"):
                    inner_resp = self.http.get(embed_url)
                    inner_soup = BeautifulSoup(inner_resp.text, "html.parser")
                    inner_f = inner_soup.select_one("iframe")
                    if inner_f:
                        inner_url = inner_f.get("src") or inner_f.get("data-src")
            except Exception:
                pass

            target_url = inner_url or embed_url
            name = self._identify_server_name(target_url)

            servers.append(
                ToonstreamStreamServer(
                    server_name=name,
                    embed_url=embed_url,
                    inner_iframe_url=inner_url,
                )
            )
        return servers

    def close(self):
        self.http.close()
