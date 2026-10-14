"""
Next.js App Router (React Server Components / RSC) parser for AnimeCube.
Extracts structured anime metadata, episode catalogs, and player configurations.
"""
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from bs4 import BeautifulSoup

from .config import PRIMARY_DOMAIN
from .models import SeriesDetail, EpisodeSummary, SearchResult, StreamServer, EpisodeDetail


class RscParser:
    @staticmethod
    def extract_full_rsc(html_content: str) -> str:
        """
        Extracts and joins all self.__next_f.push([1, "..."]) chunks from HTML.
        """
        chunks = []
        for m in re.finditer(r'self\.__next_f\.push\(\[\d+,\s*"(.*?)"\]\)', html_content):
            raw = m.group(1)
            try:
                chunks.append(raw.encode().decode('unicode-escape'))
            except Exception:
                chunks.append(raw)
        return "".join(chunks)

    @staticmethod
    def extract_balanced_json(text: str, marker: str) -> Optional[str]:
        """
        Locates marker and extracts the balanced JSON object starting at the first '{' after marker.
        """
        pos = text.find(marker)
        if pos == -1:
            return None
        start = text.find('{', pos)
        if start == -1:
            return None

        depth = 0
        in_string = False
        escape = False

        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if not in_string:
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        return text[start:i+1]
        return None

    @classmethod
    def parse_series_detail(cls, html_content: str, fallback_slug: str = "") -> SeriesDetail:
        """
        Extracts complete SeriesDetail from the Next.js RSC payload embedded in the page HTML.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        full_rsc = cls.extract_full_rsc(html_content)

        # Meta fallbacks
        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        meta_desc = soup.find("meta", attrs={"name": "description"})
        og_image = soup.find("meta", property="og:image")

        description_meta = None
        if og_desc and og_desc.get("content"):
            description_meta = og_desc["content"]
        elif meta_desc and meta_desc.get("content"):
            description_meta = meta_desc["content"]

        poster_meta = og_image["content"] if og_image and og_image.get("content") else None

        # Extract balanced JSON anime object
        anime_json_str = cls.extract_balanced_json(full_rsc, '"anime":{"title":')
        data: Dict[str, Any] = {}
        if anime_json_str:
            try:
                data = json.loads(anime_json_str)
            except Exception:
                pass

        slug = data.get("slug") or fallback_slug
        url = f"{PRIMARY_DOMAIN}/anime/{slug}"
        title = data.get("title") or (og_title["content"].split(" - ")[0] if og_title and og_title.get("content") else slug)
        cover_image = data.get("coverImage") or poster_meta
        status = data.get("status")
        year = data.get("year")
        total_episodes = data.get("totalEpisodes")
        genres = data.get("genres") or []
        tags = data.get("tags") or []
        aliases = data.get("aliases") or []
        update_days = data.get("updateDays") or []
        update_time = data.get("updateTime")

        # Synopsis handling (RSC description might be string reference like "$21")
        synopsis = data.get("description")
        if not synopsis or str(synopsis).startswith("$"):
            synopsis = description_meta

        # Episodes parsing across all primaryTabs and seasons
        episodes: List[EpisodeSummary] = []
        for tab in data.get("primaryTabs", []):
            tab_id = tab.get("id", "primary-1")
            for season in tab.get("seasons", []):
                season_id = season.get("id", "tab-1")
                for ep in season.get("episodes", []):
                    ep_id = ep.get("id") or f"{slug}-{season_id}-ep-{ep.get('number', 0)}"
                    ep_num = float(ep.get("number", 0))
                    ep_title = ep.get("title") or f"Episode {int(ep_num)}"
                    ep_url = f"{PRIMARY_DOMAIN}/anime/{slug}?season={season_id}&episode={ep_id}"

                    episodes.append(
                        EpisodeSummary(
                            episode_number=ep_num,
                            id=ep_id,
                            title=ep_title,
                            url=ep_url,
                            season_id=season_id,
                            primary_tab_id=tab_id,
                            duration=ep.get("duration"),
                            published_at=ep.get("publishedAt"),
                            thumbnail=ep.get("thumbnail")
                        )
                    )

        # Sort episodes ascending
        episodes.sort(key=lambda x: x.episode_number)

        return SeriesDetail(
            slug=slug,
            url=url,
            title=title,
            aliases=aliases,
            status=status,
            year=year,
            total_episodes=total_episodes or len(episodes),
            genres=genres,
            tags=tags,
            synopsis=synopsis,
            cover_image=cover_image,
            update_days=update_days,
            update_time=update_time,
            episodes=episodes,
            extra_meta=data
        )

    @classmethod
    def parse_catalog_from_homepage(cls, html_content: str) -> List[SearchResult]:
        """
        Extracts all series cards present in the homepage Next.js RSC payload.
        """
        full_rsc = cls.extract_full_rsc(html_content)
        catalog: List[SearchResult] = []
        seen_slugs = set()

        # Find series cards pattern in RSC or HTML
        # Look for "/anime/{slug}"
        slug_matches = set(re.findall(r'/anime/([a-zA-Z0-9_\-]+)', full_rsc + html_content))

        # Look for full card objects in RSC
        for slug in sorted(slug_matches):
            if slug in seen_slugs or slug in ("favorites", "schedule"):
                continue
            seen_slugs.add(slug)

            # Build human-readable title from slug
            title = slug.replace("-", " ").title()

            catalog.append(
                SearchResult(
                    title=title,
                    slug=slug,
                    url=f"{PRIMARY_DOMAIN}/anime/{slug}"
                )
            )

        return catalog

    @classmethod
    def build_episode_detail(
        cls,
        series: SeriesDetail,
        ep_summary: EpisodeSummary,
        servers: Optional[List[StreamServer]] = None
    ) -> EpisodeDetail:
        """
        Builds complete playback details and video embed mirrors for an episode.
        """
        if not servers:
            servers = [
                StreamServer(
                    server_name="AnimeCube Web Player",
                    provider="animecube",
                    embed_url=ep_summary.url,
                    quality="1080p / 4K",
                    languages=["Multi-Sub", "English"]
                )
            ]

        # Prev and next navigation
        prev_url = None
        next_url = None
        for i, ep in enumerate(series.episodes):
            if ep.id == ep_summary.id:
                if i > 0:
                    prev_url = series.episodes[i - 1].url
                if i < len(series.episodes) - 1:
                    next_url = series.episodes[i + 1].url
                break

        return EpisodeDetail(
            episode_number=ep_summary.episode_number,
            id=ep_summary.id,
            title=ep_summary.title,
            url=ep_summary.url,
            series_slug=series.slug,
            series_title=series.title,
            season_id=ep_summary.season_id,
            primary_tab_id=ep_summary.primary_tab_id,
            duration=ep_summary.duration,
            published_at=ep_summary.published_at,
            servers=servers,
            prev_episode=prev_url,
            next_episode=next_url
        )
