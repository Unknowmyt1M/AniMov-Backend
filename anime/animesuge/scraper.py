"""Production-Grade AnimeSuge Scraper Implementation."""

import re
import logging
from typing import List, Optional
from pathlib import Path
from bs4 import BeautifulSoup

from .config import BASE_URL, EMBED_BASE_URL, AJAX_HEADERS
from .http_client import AnimeSugeHttpClient
from .decryptor import decrypt_megaplay_sources
from .storage import AnimeSugeStorage
from .models import (
    AnimeSugeSearchResult,
    AnimeSugeSeriesDetail,
    AnimeSugeEpisode,
    AnimeSugeServer,
    AnimeSugeStreamResult,
    AnimeSugeSubtitleTrack,
    AnimeSugeSkipData,
    AnimeSugeSkipInterval,
)

logger = logging.getLogger("animesuge.scraper")


class AnimeSugeScraper:
    """Independent scraper for AnimeSuge (animesuge.cz)."""

    def __init__(self, http_client: Optional[AnimeSugeHttpClient] = None, storage: Optional[AnimeSugeStorage] = None):
        self.client = http_client or AnimeSugeHttpClient()
        self.storage = storage or AnimeSugeStorage()

    def _extract_slug(self, url_or_slug: str) -> str:
        """Normalize URL or slug to standard anime slug."""
        cleaned = url_or_slug.strip()
        if "animesuge.cz" in cleaned:
            match = re.search(r'/(?:anime|watch)/([^/?#]+)', cleaned)
            if match:
                return match.group(1)
        return cleaned.strip("/").split("/")[-1]

    def search(self, query: str, page: int = 1) -> List[AnimeSugeSearchResult]:
        """Search anime catalog on AnimeSuge."""
        url = f"{BASE_URL}/filter"
        params = {"keyword": query}
        if page > 1:
            params["page"] = str(page)

        logger.info(f"Searching AnimeSuge for: '{query}' (page {page})")
        res = self.client.get(url, params=params)
        if res.status_code != 200:
            logger.error(f"Search request failed: HTTP {res.status_code}")
            return []

        soup = BeautifulSoup(res.text, "html.parser")
        items = soup.select(".item, .film_list-wrap .flw-item")

        results: List[AnimeSugeSearchResult] = []
        for it in items:
            link_tag = it.select_one("a[href*='/anime/'], a[href*='/watch/']")
            if not link_tag:
                continue

            href = link_tag.get("href", "")
            slug = self._extract_slug(href)

            img_tag = it.select_one("img")
            poster = img_tag.get("data-src") or img_tag.get("src") if img_tag else None

            title_tag = it.select_one(".name a, .dynamic-name, h3 a, h2 a")
            title = title_tag.get_text(strip=True) if title_tag else (img_tag.get("alt") if img_tag else slug)

            type_el = it.select_one(".item-status .type, .type, .poster .right, .meta .right")
            raw_type = type_el.get_text(strip=True).upper() if type_el else "TV"
            if raw_type == "MOVIE":
                anime_type = "Anime Movie"
            elif raw_type == "TV":
                anime_type = "TV Series"
            elif raw_type:
                anime_type = raw_type
            else:
                anime_type = "TV Series"

            sub_el = it.select_one(".dub-sub-total .sub, .ep-status.sub span")
            dub_el = it.select_one(".dub-sub-total .dub, .ep-status.dub span")
            total_el = it.select_one(".dub-sub-total .total, .ep-status.total span")
            sub = sub_el.get_text(strip=True) if sub_el else ""
            dub = dub_el.get_text(strip=True) if dub_el else ""
            total = total_el.get_text(strip=True) if total_el else ""

            if raw_type == "MOVIE":
                episodes = "1 Ep (Movie)"
                duration = "Feature Film"
            else:
                ep_num = total if (total and total != "0") else (sub if sub else "1")
                episodes = f"{ep_num} eps"
                parts = []
                if sub and sub != "0":
                    parts.append(f"Sub: {sub}")
                if dub and dub != "0":
                    parts.append(f"Dub: {dub}")
                if parts:
                    episodes += f" ({', '.join(parts)})"
                duration = "~24m / ep"

            results.append(
                AnimeSugeSearchResult(
                    id=slug,
                    slug=slug,
                    title=title,
                    poster=poster,
                    anime_type=anime_type,
                    episodes=episodes,
                    duration=duration,
                    link=f"{BASE_URL}/anime/{slug}",
                )
            )

        if not results:
            for a in soup.select("a[href*='/anime/']"):
                href = a.get("href", "")
                slug = self._extract_slug(href)
                t = a.get_text(strip=True)
                if slug and t and not any(r.slug == slug for r in results):
                    results.append(
                        AnimeSugeSearchResult(
                            id=slug,
                            slug=slug,
                            title=t,
                            link=f"{BASE_URL}/anime/{slug}",
                        )
                    )

        return results

    def get_series_detail(self, slug_or_url: str, use_cache: bool = True, max_age_seconds: Optional[int] = 86400 * 7) -> Optional[AnimeSugeSeriesDetail]:
        """Fetch series details, metadata, and full episode catalog."""
        slug = self._extract_slug(slug_or_url)
        if use_cache:
            cached = self.storage.get_series(slug, max_age_seconds=max_age_seconds)
            if cached and cached.episodes:
                return cached

        anime_url = f"{BASE_URL}/anime/{slug}"
        logger.info(f"Fetching series page: {anime_url}")
        res = self.client.get(anime_url)
        if res.status_code != 200:
            logger.error(f"Failed to fetch anime page: HTTP {res.status_code}")
            return None

        soup = BeautifulSoup(res.text, "html.parser")
        watch_wrap = soup.select_one(".watch-wrap, #watch-main, [data-id]")
        if not watch_wrap:
            logger.error("Could not find watch-wrap element on page.")
            return None

        anime_id = watch_wrap.get("data-id")
        if not anime_id:
            logger.error("No data-id found in watch-wrap.")
            return None

        title_el = soup.select_one("h1.title, .film-name, h1")
        title = title_el.get_text(strip=True) if title_el else slug.replace("-", " ").title()

        poster_el = soup.select_one(".poster img, .film-poster-img")
        poster = poster_el.get("src") or poster_el.get("data-src") if poster_el else None

        synopsis_el = soup.select_one(".synopsis, .description, .film-description")
        synopsis = synopsis_el.get_text(strip=True) if synopsis_el else None

        # Parse scoped metadata block for genres, status, and anime_type
        meta_el = soup.select_one(".meta, .film-info")
        genres: List[str] = []
        status: Optional[str] = None
        anime_type: Optional[str] = None

        if meta_el:
            genres = [
                g.get_text(strip=True)
                for g in meta_el.select("a[href*='/genre/']")
                if g.get_text(strip=True)
            ]
            for item in meta_el.find_all("div", recursive=False):
                header = item.find("div")
                val_el = item.find("span")
                if header and val_el:
                    k = header.get_text(strip=True).rstrip(":").lower()
                    v = val_el.get_text(strip=True)
                    if k == "type":
                        anime_type = v
                    elif k == "status":
                        status = v

        if not genres:
            genres = [
                g.get_text(strip=True)
                for g in soup.select(".item-title a[href*='/genre/'], .fdi-item a[href*='/genre/']")
                if g.get_text(strip=True)
            ]
        genres = list(dict.fromkeys(genres))

        # Fetch episodes via AJAX
        ep_url = f"{BASE_URL}/ajax/episode/list/{anime_id}"
        logger.info(f"Fetching episode list from: {ep_url}")
        ep_res = self.client.get(ep_url, headers=AJAX_HEADERS)
        episodes: List[AnimeSugeEpisode] = []

        if ep_res.status_code == 200:
            try:
                ep_json = ep_res.json()
                ep_html = ep_json.get("result", "")
                ep_soup = BeautifulSoup(ep_html, "html.parser")
                for a in ep_soup.select("a[data-id]"):
                    ep_id = a.get("data-id")
                    num_str = a.get("data-slug") or a.get("data-num") or "0"
                    try:
                        ep_num = int(float(num_str))
                    except ValueError:
                        ep_num = len(episodes) + 1

                    ep_slug = a.get("data-slug") or str(ep_num)
                    ep_title = a.get("title") or a.get_text(strip=True) or f"Episode {ep_num}"
                    server_param = a.get("data-ids") or ""
                    has_sub = a.get("data-sub") == "1"
                    has_dub = a.get("data-dub") == "1"

                    ts_val = a.get("data-timestamp")
                    timestamp = int(ts_val) if ts_val and ts_val.isdigit() else None

                    episodes.append(
                        AnimeSugeEpisode(
                            id=ep_id,
                            episode_num=ep_num,
                            slug=ep_slug,
                            title=ep_title,
                            server_param=server_param,
                            has_sub=has_sub,
                            has_dub=has_dub,
                            timestamp=timestamp,
                        )
                    )
            except Exception as e:
                logger.error(f"Error parsing episodes list: {e}")

        detail = AnimeSugeSeriesDetail(
            anime_id=anime_id,
            slug=slug,
            title=title,
            poster=poster,
            synopsis=synopsis,
            anime_type=anime_type,
            status=status,
            genres=genres,
            total_episodes=len(episodes),
            episodes=episodes,
        )

        self.storage.save_series(detail)
        return detail

    def get_episode_servers(self, server_param: str) -> List[AnimeSugeServer]:
        """Fetch available server mirrors for an episode using its server_param."""
        if not server_param:
            return []

        url = f"{BASE_URL}/ajax/server/list"
        res = self.client.get(url, params={"servers": server_param}, headers=AJAX_HEADERS)
        if res.status_code != 200:
            logger.error(f"Failed to fetch servers: HTTP {res.status_code}")
            return []

        try:
            data = res.json()
            html = data.get("result", "")
            soup = BeautifulSoup(html, "html.parser")
            servers: List[AnimeSugeServer] = []

            for s in soup.select("[data-link-id]"):
                link_id = s.get("data-link-id")
                name = s.get_text(strip=True)
                parent_type = s.find_parent(class_="type")
                stype = parent_type.get("data-type") if parent_type else "sub"

                servers.append(
                    AnimeSugeServer(
                        name=name,
                        link_id=link_id,
                        server_type=stype,
                    )
                )
            return servers
        except Exception as e:
            logger.error(f"Error parsing server list: {e}")
            return []

    def get_stream_detail(
        self,
        episode_id: str,
        episode_num: int,
        link_id: str,
        server_name: str,
        server_type: str = "sub",
        use_cache: bool = True,
    ) -> Optional[AnimeSugeStreamResult]:
        """Fetch stream embed URL, query player sources, and decrypt master m3u8 playlist."""
        if use_cache:
            cached = self.storage.get_stream(episode_id, server_name, server_type)
            if cached and cached.master_m3u8:
                return cached

        # Step 1: Query server embed URL
        srv_url = f"{BASE_URL}/ajax/server"
        res = self.client.get(srv_url, params={"get": link_id}, headers=AJAX_HEADERS)
        if res.status_code != 200:
            logger.error(f"Failed to resolve server link: HTTP {res.status_code}")
            return None

        try:
            srv_json = res.json()
            result_data = srv_json.get("result", {})
            embed_url = result_data.get("url")
            raw_skip = result_data.get("skip_data") or {}

            skip_data = None
            if raw_skip:
                intro = raw_skip.get("intro")
                outro = raw_skip.get("outro")
                skip_data = AnimeSugeSkipData(
                    intro=AnimeSugeSkipInterval(start=intro[0], end=intro[1]) if intro and len(intro) >= 2 else None,
                    outro=AnimeSugeSkipInterval(start=outro[0], end=outro[1]) if outro and len(outro) >= 2 else None,
                )

            if not embed_url:
                logger.error("No embed URL returned by AnimeSuge.")
                return None

            # Step 2: Fetch embed player page to find data-id of player
            embed_res = self.client.get(embed_url, headers={"Referer": f"{BASE_URL}/"})
            if embed_res.status_code != 200:
                logger.error(f"Failed to fetch embed page {embed_url}: HTTP {embed_res.status_code}")
                return AnimeSugeStreamResult(
                    episode_id=episode_id,
                    episode_num=episode_num,
                    server_name=server_name,
                    server_type=server_type,
                    embed_url=embed_url,
                    skip_data=skip_data,
                )

            embed_soup = BeautifulSoup(embed_res.text, "html.parser")
            player_el = embed_soup.select_one("#megaplay-player")
            player_id = player_el.get("data-id") if player_el else None

            master_m3u8 = None
            subtitles: List[AnimeSugeSubtitleTrack] = []
            raw_sources = None

            if player_id:
                # Step 3: Fetch stream/getSourcesNew endpoint
                sources_url = f"{EMBED_BASE_URL}/stream/getSourcesNew"
                sources_res = self.client.get(
                    sources_url,
                    params={"id": player_id},
                    headers={"Referer": embed_url, "X-Requested-With": "XMLHttpRequest"},
                )

                if sources_res.status_code == 200:
                    sources_json = sources_res.json()
                    enc_payload = sources_json.get("enc")

                    for tr in sources_json.get("tracks", []):
                        if tr.get("file"):
                            subtitles.append(
                                AnimeSugeSubtitleTrack(
                                    file=tr.get("file"),
                                    label=tr.get("label", "Unknown"),
                                    kind=tr.get("kind", "captions"),
                                    default=bool(tr.get("default", False)),
                                )
                            )

                    if not skip_data:
                        src_intro = sources_json.get("intro")
                        src_outro = sources_json.get("outro")
                        if src_intro or src_outro:
                            skip_data = AnimeSugeSkipData(
                                intro=AnimeSugeSkipInterval(start=src_intro.get("start"), end=src_intro.get("end")) if src_intro else None,
                                outro=AnimeSugeSkipInterval(start=src_outro.get("start"), end=src_outro.get("end")) if src_outro else None,
                            )

                    # Step 4: Decrypt AES-256-CBC enc payload
                    if enc_payload:
                        decrypted = decrypt_megaplay_sources(enc_payload)
                        if decrypted and decrypted.get("file"):
                            master_m3u8 = decrypted["file"]
                            raw_sources = decrypted

            stream_res = AnimeSugeStreamResult(
                episode_id=episode_id,
                episode_num=episode_num,
                server_name=server_name,
                server_type=server_type,
                embed_url=embed_url,
                master_m3u8=master_m3u8,
                subtitles=subtitles,
                skip_data=skip_data,
                headers={"Referer": f"{EMBED_BASE_URL}/"},
                raw_sources=raw_sources,
            )

            self.storage.save_stream(stream_res)
            return stream_res

        except Exception as e:
            logger.error(f"Error resolving stream detail: {e}")
            return None

    def crawl_series(
        self,
        slug_or_url: str,
        max_episodes: Optional[int] = None,
        server_type: str = "sub"
    ) -> Optional[AnimeSugeSeriesDetail]:
        """Crawl series and pre-fetch streams for episodes."""
        detail = self.get_series_detail(slug_or_url)
        if not detail or not detail.episodes:
            return detail

        target_episodes = detail.episodes[:max_episodes] if max_episodes else detail.episodes
        logger.info(f"Crawling {len(target_episodes)} episodes for '{detail.title}'...")

        for ep in target_episodes:
            if not ep.servers:
                ep.servers = self.get_episode_servers(ep.server_param)

            matching = [s for s in ep.servers if s.server_type == server_type] or ep.servers
            if matching:
                srv = matching[0]
                self.get_stream_detail(
                    episode_id=ep.id,
                    episode_num=ep.episode_num,
                    link_id=srv.link_id,
                    server_name=srv.name,
                    server_type=srv.server_type,
                )

        return detail

    def close(self):
        """Close HTTP client session."""
        self.client.close()
