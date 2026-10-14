"""Production-Grade Anikoto Scraper Implementation."""

import re
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from bs4 import BeautifulSoup

from .config import BASE_URL, EMBED_BASE_URL, AJAX_HEADERS, DEFAULT_HEADERS
from .http_client import AnikotoHttpClient
from .decryptor import decrypt_megaplay_sources
from .storage import AnikotoStorage
from .models import (
    AnikotoSearchResult,
    AnikotoSeriesDetail,
    AnikotoEpisode,
    AnikotoServer,
    AnikotoStreamResult,
    AnikotoSubtitleTrack,
    AnikotoSkipData,
    AnikotoSkipInterval,
)

logger = logging.getLogger("anikoto.scraper")


class AnikotoScraper:
    """Independent scraper for Anikoto (anikoto.cz)."""

    def __init__(self, http_client: Optional[AnikotoHttpClient] = None, storage: Optional[AnikotoStorage] = None):
        self.client = http_client or AnikotoHttpClient()
        self.storage = storage or AnikotoStorage()
    def _extract_slug(self, url_or_slug: str) -> str:
        """Normalize URL or slug to standard anime slug."""
        cleaned = url_or_slug.strip()
        if "anikoto.cz" in cleaned:
            # e.g. https://anikoto.cz/watch/solo-leveling-season-2-arise-from-the-shadow-3eukp/ep-1
            match = re.search(r'/watch/([^/?#]+)', cleaned)
            if match:
                return match.group(1)
        raw = cleaned.strip("/").split("/")[-1]
        return re.sub(r'[\s_]+', '-', raw)

    def search(self, query: str, page: int = 1) -> List[AnikotoSearchResult]:
        """Search anime catalog on Anikoto.

        Args:
            query: Anime title to search.
            page: Pagination page index.

        Returns:
            List of AnikotoSearchResult.
        """
        url = f"{BASE_URL}/filter"
        params = {"keyword": query}
        if page > 1:
            params["page"] = str(page)

        logger.info(f"Searching Anikoto for: '{query}' (page {page})")
        res = self.client.get(url, params=params)
        if res.status_code != 200:
            logger.error(f"Search request failed: HTTP {res.status_code}")
            return []

        soup = BeautifulSoup(res.text, "html.parser")
        items = soup.select(".film_list-wrap .flw-item") or soup.select(".item")

        results: List[AnikotoSearchResult] = []
        for it in items:
            link_tag = it.select_one("a.film-poster-ahref, a[href*='/watch/']")
            if not link_tag:
                continue

            href = link_tag.get("href", "")
            slug = self._extract_slug(href)

            img_tag = it.select_one("img.film-poster-img, img")
            poster = img_tag.get("data-src") or img_tag.get("src") if img_tag else None

            # 1. Title
            title_tag = it.select_one(".name, .d-title, .film-name a, h3 a")
            title = title_tag.get_text(strip=True) if title_tag else (img_tag.get("alt") if img_tag else slug)

            # 2. Anime Type (TV Series vs Movie vs Special vs OVA)
            type_tag = it.select_one(".poster .right, .meta .right")
            raw_type = type_tag.get_text(strip=True).upper() if type_tag else None
            if not raw_type:
                for m in it.select(".m-item label"):
                    lbl = m.get_text(strip=True).upper()
                    if lbl in ("TV", "MOVIE", "OVA", "ONA", "SPECIAL"):
                        raw_type = lbl
                        break
            if raw_type == "MOVIE":
                anime_type = "Anime Movie"
            elif raw_type == "TV":
                anime_type = "TV Series"
            elif raw_type:
                anime_type = raw_type
            else:
                anime_type = "TV Series"

            # 3. Episodes (Total, Sub, Dub counts)
            total_el = it.select_one(".ep-status.total span")
            sub_el = it.select_one(".ep-status.sub span")
            dub_el = it.select_one(".ep-status.dub span")
            total_val = total_el.get_text(strip=True) if total_el else ""
            sub_val = sub_el.get_text(strip=True) if sub_el else ""
            dub_val = dub_el.get_text(strip=True) if dub_el else ""

            if raw_type == "MOVIE":
                episodes = "1 Ep (Movie)"
                duration = "Feature Film"
            else:
                ep_count = total_val if (total_val and total_val != "0") else (sub_val if sub_val else "1")
                episodes = f"{ep_count} eps"
                parts = []
                if sub_val and sub_val != "0":
                    parts.append(f"Sub: {sub_val}")
                if dub_val and dub_val != "0":
                    parts.append(f"Dub: {dub_val}")
                if parts:
                    episodes += f" ({', '.join(parts)})"
                duration = "~24m / ep"

            # 4. Rating / Score
            rate_el = it.select_one(".m-item.rated span")
            score = rate_el.get_text(strip=True) if rate_el else None

            results.append(
                AnikotoSearchResult(
                    id=slug,
                    slug=slug,
                    title=title,
                    poster=poster,
                    anime_type=anime_type,
                    episodes=episodes,
                    duration=duration,
                    score=score,
                    link=f"{BASE_URL}/watch/{slug}",
                )
            )

        # Fallback if no .flw-item, restricted to main search results area
        if not results:
            main_container = soup.select_one(".film_list-wrap, .block_area-films, .film_list")
            if main_container:
                for a in main_container.select("a[href*='/watch/']"):
                    href = a.get("href", "")
                    slug = self._extract_slug(href)
                    title_elem = a.select_one(".name, .d-title, .film-name, h3, h2")
                    title_text = title_elem.get_text(strip=True) if title_elem else a.get("title")
                    if not title_text:
                        # Extract text while ignoring meta badges
                        clone = BeautifulSoup(str(a), "html.parser")
                        for badge in clone.select(".score, .rated, .type, .duration, .meta, .tick, .fdi-item, .m-item"):
                            badge.decompose()
                        title_text = clone.get_text(strip=True)

                    if slug and title_text and not any(r.slug == slug for r in results):
                        results.append(
                            AnikotoSearchResult(
                                id=slug,
                                slug=slug,
                                title=title_text,
                                link=f"{BASE_URL}/watch/{slug}",
                            )
                        )

        return results

    def get_series_detail(
        self,
        slug_or_url: str,
        use_cache: bool = True,
        max_age_seconds: Optional[int] = 86400 * 7,
    ) -> Optional[AnikotoSeriesDetail]:
        """Fetch series details, metadata, and full episode catalog.

        Args:
            slug_or_url: Series URL or slug.
            use_cache: If True, return from SQLite cache when available.
            max_age_seconds: Maximum cache age in seconds.

        Returns:
            AnikotoSeriesDetail or None.
        """
        slug = self._extract_slug(slug_or_url)
        if use_cache:
            cached = self.storage.get_series(slug, max_age_seconds=max_age_seconds)
            if cached and cached.episodes:
                logger.debug(f"Loaded {slug} from cache.")
                return cached

        watch_url = f"{BASE_URL}/watch/{slug}"
        logger.info(f"Fetching series page: {watch_url}")
        res = self.client.get(watch_url)

        # Handle 404 or missing watch-main (e.g. if user passed bare slug without unique hash suffix)
        if res.status_code == 404 or (res.status_code == 200 and not BeautifulSoup(res.text, "html.parser").select_one("#watch-main")):
            logger.info(f"Direct slug '{slug}' not found on Anikoto, searching for candidate slug...")
            search_query = slug.replace("-", " ").strip()
            candidates = self.search(search_query) if len(search_query) >= 2 else []
            matched_slug = None
            slug_clean = slug.lower().strip()
            slug_words = [w for w in slug_clean.split("-") if len(w) > 1]

            for cand in candidates:
                cand_clean = cand.slug.lower().strip()
                if cand_clean == slug_clean or cand_clean.startswith(f"{slug_clean}-") or cand_clean.rsplit("-", 1)[0] == slug_clean:
                    matched_slug = cand.slug
                    break

            if not matched_slug and candidates and len(slug_words) >= 2:
                for cand in candidates:
                    cand_words = set(cand.slug.lower().split("-"))
                    if set(slug_words).issubset(cand_words):
                        matched_slug = cand.slug
                        break

            if matched_slug and matched_slug != slug:
                logger.info(f"Resolved slug '{slug}' -> '{matched_slug}'")
                slug = matched_slug
                if use_cache:
                    cached = self.storage.get_series(slug, max_age_seconds=max_age_seconds)
                    if cached and cached.episodes:
                        return cached
                watch_url = f"{BASE_URL}/watch/{slug}"
                res = self.client.get(watch_url)

        if res.status_code != 200:
            logger.error(f"Failed to fetch series watch page: HTTP {res.status_code}")
            return None

        soup = BeautifulSoup(res.text, "html.parser")
        watch_main = soup.select_one("#watch-main")
        if not watch_main:
            logger.error("Could not find #watch-main element on page.")
            return None

        anime_id = watch_main.get("data-id")
        if not anime_id:
            logger.error("No data-id found in #watch-main.")
            return None

        # Extract Metadata
        title_el = soup.select_one("h1.title, .anisc-detail .film-name, h2.film-name")
        title = title_el.get_text(strip=True) if title_el else slug.replace("-", " ").title()

        poster_el = soup.select_one(".poster img, .cover img, .film-poster-img, .anisc-poster img")
        poster = poster_el.get("src") or poster_el.get("data-src") if poster_el else None

        synopsis_el = soup.select_one(".synopsis .content, .synopsis, .film-description .text, .anisc-info-wrap .synopsis, .description")
        synopsis = synopsis_el.get_text(strip=True) if synopsis_el else None

        genres = [g.get_text(strip=True) for g in soup.select(".meta a[href*='/genre/'], .anisc-info a[href*='/genre/']")]
        if not genres:
            genres = [g.get_text(strip=True) for g in soup.find_all("a", href=lambda h: h and "anikoto.cz/genre/" in h)]
        genres = list(dict.fromkeys([g for g in genres if g]))

        status_el = soup.select_one(".meta a[href*='/status/'], .anisc-info a[href*='/status/']")
        if status_el:
            status = status_el.get_text(strip=True)
        else:
            status_text = soup.find(string=re.compile(r"Status:", re.I))
            status = status_text.find_next().get_text(strip=True) if status_text and status_text.find_next() else None

        # Fetch episodes via AJAX
        ep_url = f"{BASE_URL}/ajax/episode/list/{anime_id}"
        logger.info(f"Fetching episode list from: {ep_url}")
        ep_res = self.client.get(ep_url, headers=AJAX_HEADERS)
        episodes: List[AnikotoEpisode] = []

        if ep_res.status_code == 200:
            try:
                ep_json = ep_res.json()
                ep_html = ep_json.get("result", "")
                ep_soup = BeautifulSoup(ep_html, "html.parser")
                for a in ep_soup.select("a[data-id]"):
                    ep_id = a.get("data-id")
                    num_str = a.get("data-num") or a.get("data-slug") or "0"
                    try:
                        ep_num = int(float(num_str))
                    except ValueError:
                        ep_num = len(episodes) + 1

                    ep_slug = a.get("data-slug") or str(ep_num)
                    span_el = a.select_one("span")
                    if span_el and span_el.get_text(strip=True):
                        ep_title = span_el.get_text(strip=True)
                    elif a.get("title") and a.get("title").strip():
                        ep_title = a.get("title").strip()
                    else:
                        raw_title = a.get_text(strip=True)
                        if str(ep_num) and raw_title.startswith(str(ep_num)):
                            ep_title = raw_title[len(str(ep_num)):].strip() or raw_title
                        else:
                            ep_title = raw_title
                    server_param = a.get("data-ids") or ""
                    has_sub = a.get("data-sub") == "1"
                    has_dub = a.get("data-dub") == "1"

                    ts_val = a.get("data-timestamp")
                    timestamp = int(ts_val) if ts_val and ts_val.isdigit() else None

                    episodes.append(
                        AnikotoEpisode(
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

        detail = AnikotoSeriesDetail(
            anime_id=anime_id,
            slug=slug,
            title=title,
            poster=poster,
            synopsis=synopsis,
            status=status,
            genres=genres,
            total_episodes=len(episodes),
            episodes=episodes,
        )

        self.storage.save_series(detail)
        return detail

    def get_episode_servers(self, server_param: str) -> List[AnikotoServer]:
        """Fetch available server mirrors for an episode using its server_param.

        Args:
            server_param: Encrypted data-ids value from episode anchor.

        Returns:
            List of AnikotoServer.
        """
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
            servers: List[AnikotoServer] = []

            for s in soup.select("[data-link-id]"):
                link_id = s.get("data-link-id")
                name = s.get_text(strip=True)
                parent_type = s.find_parent(class_="type")
                stype = parent_type.get("data-type") if parent_type else "sub"

                servers.append(
                    AnikotoServer(
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
    ) -> Optional[AnikotoStreamResult]:
        """Fetch stream embed URL, query player sources, and decrypt master m3u8 playlist.

        Args:
            episode_id: Anikoto episode ID.
            episode_num: Episode number.
            link_id: Server data-link-id.
            server_name: Server mirror name.
            server_type: 'sub' or 'dub'.
            use_cache: If True, check SQLite database first.

        Returns:
            AnikotoStreamResult with decrypted master_m3u8, subtitles, and skip_data.
        """
        if use_cache:
            cached = self.storage.get_stream(episode_id, server_name, server_type)
            if cached and cached.master_m3u8:
                return cached

        # Step 1: Query Anikoto server embed URL
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
                skip_data = AnikotoSkipData(
                    intro=AnikotoSkipInterval(start=intro[0], end=intro[1]) if intro and len(intro) >= 2 else None,
                    outro=AnikotoSkipInterval(start=outro[0], end=outro[1]) if outro and len(outro) >= 2 else None,
                )

            if not embed_url:
                logger.error("No embed URL returned by Anikoto.")
                return None

            # Step 2: Fetch embed player page to find data-id of player
            embed_res = self.client.get(embed_url, headers={"Referer": f"{BASE_URL}/"})
            if embed_res.status_code != 200:
                logger.error(f"Failed to fetch embed page {embed_url}: HTTP {embed_res.status_code}")
                return AnikotoStreamResult(
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
            subtitles: List[AnikotoSubtitleTrack] = []
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

                    # Extract Subtitles
                    for tr in sources_json.get("tracks", []):
                        if tr.get("file"):
                            subtitles.append(
                                AnikotoSubtitleTrack(
                                    file=tr.get("file"),
                                    label=tr.get("label", "Unknown"),
                                    kind=tr.get("kind", "captions"),
                                    default=bool(tr.get("default", False)),
                                )
                            )

                    # Extract intro/outro from sources if not already present
                    if not skip_data:
                        src_intro = sources_json.get("intro")
                        src_outro = sources_json.get("outro")
                        if src_intro or src_outro:
                            skip_data = AnikotoSkipData(
                                intro=AnikotoSkipInterval(start=src_intro.get("start"), end=src_intro.get("end")) if src_intro else None,
                                outro=AnikotoSkipInterval(start=src_outro.get("start"), end=src_outro.get("end")) if src_outro else None,
                            )

                    # Step 4: Decrypt AES-256-CBC enc payload
                    if enc_payload:
                        decrypted = decrypt_megaplay_sources(enc_payload)
                        if decrypted and decrypted.get("file"):
                            master_m3u8 = decrypted["file"]
                            raw_sources = decrypted

            stream_res = AnikotoStreamResult(
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
    ) -> Optional[AnikotoSeriesDetail]:
        """Crawl series and pre-fetch streams for episodes."""
        detail = self.get_series_detail(slug_or_url)
        if not detail or not detail.episodes:
            return detail

        target_episodes = detail.episodes[:max_episodes] if max_episodes else detail.episodes
        logger.info(f"Crawling {len(target_episodes)} episodes for '{detail.title}'...")

        for ep in target_episodes:
            if not ep.servers:
                ep.servers = self.get_episode_servers(ep.server_param)

            # Filter preferred server
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
