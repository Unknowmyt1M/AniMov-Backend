"""
High-level scraper engine for Miruro Anime.
Orchestrates API queries, XOR-Gzip response decryption, Keeply stream deobfuscation, and database persistence.
"""
import re
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger("miruro.scraper")

from .config import API_BASE, PRIMARY_DOMAIN
from .http_client import HttpClient
from .decryptor import MiruroDecryptor
from .storage import Storage
from .models import (
    SeriesDetail,
    EpisodeDetail,
    EpisodeSummary,
    SearchResult,
    StreamMirror,
    SubtitleTrack
)


class MiruroScraper:
    def __init__(self, cache_enabled: bool = True):
        self.http = HttpClient(cache_enabled=cache_enabled)
        self.storage = Storage()

    def _extract_anime_id(self, id_or_url: str) -> str:
        """
        Extracts the 32-character Miruro ID from an input ID, URL, AniList ID, or slug.
        Example: https://www.miruro.cx/watch/ZkbbIfGqvoOrvvss5iQuAlVkW4AaYPxz/one-piece -> ZkbbIfGqvoOrvvss5iQuAlVkW4AaYPxz
        """
        clean = id_or_url.strip()
        if "/watch/" in clean:
            clean = clean.split("/watch/")[1].split("/")[0]
        elif "/info/" in clean:
            clean = clean.split("/info/")[1].split("/")[0]
        clean = clean.split("?")[0].strip("/ ")

        # If it's already a 32-character Miruro opaque ID
        if len(clean) == 32 and re.match(r"^[A-Za-z0-9_-]{32}$", clean):
            return clean

        # If it's an AniList integer ID (e.g. 20, 16498)
        if clean.isdigit():
            try:
                lookup_url = f"{API_BASE}/anime?anilist_id_in={clean}&limit=100"
                lookup_data = self.http.get_decoded_json(lookup_url)
                for entry in lookup_data.get("data", []):
                    m_id = entry.get("id")
                    if m_id:
                        return m_id
            except Exception as e:
                logger.warning(f"Miruro lookup by AniList ID failed: {e}")

        # If it's a bare slug or title, try resolving via AniList search first
        try:
            results = self.search(clean, limit=5)
            if results and results[0].id and len(results[0].id) == 32:
                return results[0].id
        except Exception:
            pass

        return clean

    def search(self, query: str, limit: int = 20) -> List[SearchResult]:
        """
        Searches Miruro anime catalog using AniList GraphQL backend and resolves Miruro opaque IDs.
        """
        clean_q = query.strip()
        gql_query = """
        query ($search: String, $perPage: Int) {
          Page(page: 1, perPage: $perPage) {
            media(search: $search, type: ANIME, sort: POPULARITY_DESC) {
              id
              title {
                english
                romaji
                native
              }
              format
              status
              episodes
              duration
              seasonYear
              averageScore
              genres
              coverImage {
                large
              }
            }
          }
        }
        """
        try:
            resp = self.http.session.post(
                "https://graphql.anilist.co",
                json={"query": gql_query, "variables": {"search": clean_q, "perPage": limit}},
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=self.http.timeout,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {}).get("Page", {}).get("media", [])
                
                # Batch-resolve AniList IDs to Miruro 32-character opaque IDs
                anilist_ids = [str(item["id"]) for item in data if item.get("id")]
                anilist_to_miruro: Dict[str, str] = {}
                bridge_error = None
                if anilist_ids:
                    try:
                        lookup_url = f"{API_BASE}/anime?anilist_id_in={','.join(anilist_ids[:100])}&limit=100"
                        lookup_data = self.http.get_decoded_json(lookup_url)
                        for entry in lookup_data.get("data", []):
                            m_id = entry.get("id")
                            if m_id:
                                for al_id in entry.get("external_ids", {}).get("anilist", []):
                                    anilist_to_miruro[str(al_id)] = m_id
                    except Exception as e:
                        bridge_error = e
                        logger.warning(f"Miruro opaque ID batch lookup failed: {e}")

                if anilist_ids and not anilist_to_miruro and bridge_error:
                    raise RuntimeError(f"Miruro catalog bridge unavailable: {bridge_error}")

                results: List[SearchResult] = []
                for item in data:
                    al_id_str = str(item.get("id", ""))
                    miruro_id = anilist_to_miruro.get(al_id_str)
                    if not miruro_id:
                        # Skip entries that have no mapping on Miruro catalog
                        continue

                    t = item.get("title", {})
                    title = t.get("english") or t.get("romaji") or t.get("native") or "Unknown Title"
                    raw_fmt = item.get("format")
                    if raw_fmt == "MOVIE":
                        fmt_str = "Anime Movie"
                    elif raw_fmt == "TV":
                        fmt_str = "TV Series"
                    elif raw_fmt:
                        fmt_str = raw_fmt
                    else:
                        fmt_str = "TV Series"

                    eps_num = item.get("episodes")
                    if raw_fmt == "MOVIE":
                        episodes_str = "1 Ep (Movie)"
                    elif eps_num:
                        episodes_str = f"{eps_num} eps"
                    else:
                        episodes_str = "Ongoing"

                    dur_num = item.get("duration")
                    if dur_num:
                        dur_str = f"{dur_num}m / ep" if raw_fmt != "MOVIE" else f"{dur_num}m"
                    else:
                        dur_str = "~24m / ep" if raw_fmt != "MOVIE" else "Feature Film"

                    cover = item.get("coverImage", {}).get("large")

                    results.append(
                        SearchResult(
                            id=miruro_id,
                            title=title,
                            title_romaji=t.get("romaji"),
                            format=fmt_str,
                            status=item.get("status"),
                            year=item.get("seasonYear"),
                            episode_count=eps_num,
                            duration=dur_str,
                            average_score=float(item.get("averageScore")) if item.get("averageScore") else None,
                            cover_url=cover,
                            genres=item.get("genres", []),
                        )
                    )
                return results
        except Exception as e:
            logger.warning(f"AniList GraphQL search failed: {e}")

        # Fallback to direct catalog endpoint if GraphQL unreachable
        url = f"{API_BASE}/anime?q={clean_q}&limit={limit}&sort=-popularity"
        data = self.http.get_decoded_json(url)
        results: List[SearchResult] = []
        for item in data.get("data", []):
            t = item.get("title", {})
            title = t.get("english") or t.get("romaji") or t.get("native") or "Unknown Title"
            results.append(
                SearchResult(
                    id=str(item.get("id", "")),
                    title=title,
                    title_romaji=t.get("romaji"),
                    format=item.get("format") or "TV Series",
                    status=item.get("status"),
                    year=item.get("season_year"),
                    episode_count=item.get("episode_count"),
                    duration="~24m / ep",
                    cover_url=item.get("cover_url"),
                    genres=item.get("genres", [])
                )
            )
        return results

    def get_series_detail(self, id_or_url: str) -> SeriesDetail:
        """
        Fetches complete series metadata and episode list for a Miruro anime.
        """
        anime_id = self._extract_anime_id(id_or_url)
        
        # 1. Fetch Anime Info
        info_url = f"{API_BASE}/anime/{anime_id}"
        info_data = self.http.get_decoded_json(info_url)
        if not info_data:
            raise ValueError(f"Anime ID '{anime_id}' not found on Miruro.")

        # 2. Fetch Episodes List
        ep_url = f"{API_BASE}/anime/{anime_id}/episodes?limit=10000"
        ep_data = self.http.get_decoded_json(ep_url)
        raw_episodes = ep_data.get("data", [])

        episodes: List[EpisodeSummary] = []
        for ep in raw_episodes:
            ep_num = float(ep.get("episode_number", 0))
            ep_title = ep.get("title") or f"Episode {int(ep_num)}"
            episodes.append(
                EpisodeSummary(
                    id=ep.get("id") or f"{anime_id}-{int(ep_num)}",
                    episode_number=ep_num,
                    title=ep_title,
                    thumbnail_url=ep.get("thumbnail_url"),
                    duration_minutes=ep.get("duration_minutes"),
                    aired_at=ep.get("aired_at")
                )
            )

        episodes.sort(key=lambda x: x.episode_number)

        t = info_data.get("title", {})
        raw_genres = info_data.get("genres", [])
        genres = [g.get("name") if isinstance(g, dict) else str(g) for g in raw_genres if g]
        raw_tags = info_data.get("tags", [])
        tags = [t.get("name") if isinstance(t, dict) else str(t) for t in raw_tags if t]
        raw_studios = info_data.get("studios", [])
        studios = [s.get("name") if isinstance(s, dict) else str(s) for s in raw_studios if s]

        series = SeriesDetail(
            id=anime_id,
            title_english=t.get("english"),
            title_romaji=t.get("romaji"),
            title_native=t.get("native"),
            format=info_data.get("format"),
            status=info_data.get("status"),
            season=info_data.get("season"),
            season_year=info_data.get("season_year"),
            episode_count=info_data.get("episode_count") or len(episodes),
            average_score=float(info_data.get("average_score") or 0.0),
            popularity=info_data.get("popularity"),
            cover_url=info_data.get("cover_url"),
            banner_url=info_data.get("banner_url"),
            genres=genres,
            tags=tags,
            studios=studios,
            description=info_data.get("description"),
            episodes=episodes,
            external_ids=info_data.get("external_ids", {})
        )

        self.storage.save_series(series)
        return series

    def get_episode_detail(self, id_or_url: str, episode_number: float) -> EpisodeDetail:
        """
        Fetches, decrypts, and organizes all streaming servers, mirrors, direct .m3u8 playlists,
        embeds, and subtitle tracks for a specific episode.
        """
        anime_id = self._extract_anime_id(id_or_url)
        ep_num_int = int(episode_number) if episode_number.is_integer() else episode_number
        
        play_url = f"{API_BASE}/anime/{anime_id}/episodes/{ep_num_int}/play"
        play_data = self.http.get_decoded_json(play_url)
        if not play_data or not play_data.get("tracks"):
            raise ValueError(f"Episode {ep_num_int} for anime '{anime_id}' not found on Miruro.")

        servers: List[StreamMirror] = []
        subtitles: List[SubtitleTrack] = []
        downloads: List[Dict[str, Any]] = []

        seen_sub_urls = set()

        for track_item in play_data.get("tracks", []):
            track_type = track_item.get("track", "sub")  # 'sub', 'ssub', 'dub'
            for provider_item in track_item.get("providers", []):
                prov_name = provider_item.get("provider", "unknown")

                # Collect Subtitles
                for sub in provider_item.get("subtitles", []):
                    sub_file = sub.get("file", "")
                    if sub_file and sub_file not in seen_sub_urls:
                        seen_sub_urls.add(sub_file)
                        subtitles.append(
                            SubtitleTrack(
                                language=sub.get("language", "en"),
                                label=sub.get("label", sub.get("language", "English")),
                                file=sub_file,
                                format=sub.get("format", "vtt"),
                                default=sub.get("default", False)
                            )
                        )

                # Collect Downloads
                for dl in provider_item.get("downloads", []):
                    downloads.append({
                        "provider": prov_name,
                        "track": track_type,
                        "url": dl.get("url"),
                        "quality": dl.get("quality"),
                        "size": dl.get("size")
                    })

                # Collect Servers and Streams
                for srv in provider_item.get("servers", []):
                    srv_name = srv.get("server", prov_name)
                    headers = srv.get("headers", {})
                    embed_info = srv.get("embed")
                    embed_url = embed_info.get("url") if isinstance(embed_info, dict) else None

                    streams = srv.get("streams", [])
                    if streams:
                        for st in streams:
                            stream_url = st.get("url")
                            raw_upstream = None
                            if stream_url and "keeply.top" in stream_url:
                                raw_upstream = MiruroDecryptor.deobfuscate_keeply_url(stream_url)

                            servers.append(
                                StreamMirror(
                                    server_name=f"{prov_name.title()} - {srv_name} [{track_type.upper()}]",
                                    provider=prov_name,
                                    track_type=track_type,
                                    format=st.get("format", "hls"),
                                    url=stream_url,
                                    embed_url=embed_url,
                                    quality=st.get("quality") or "1080p / Multi-Quality",
                                    raw_upstream_url=raw_upstream,
                                    headers=headers,
                                    extra_data=st
                                )
                            )
                    elif embed_url:
                        # Server only has embed URL
                        servers.append(
                            StreamMirror(
                                server_name=f"{prov_name.title()} - {srv_name} [Embed {track_type.upper()}]",
                                provider=prov_name,
                                track_type=track_type,
                                format="embed",
                                url=None,
                                embed_url=embed_url,
                                quality="Embed Player",
                                headers=headers
                            )
                        )

        # Fallback web player link
        servers.append(
            StreamMirror(
                server_name="Miruro Web Player",
                provider="miruro",
                track_type="web",
                format="web",
                embed_url=f"{PRIMARY_DOMAIN}/watch/{anime_id}?ep={ep_num_int}",
                quality="1080p Multi-Quality"
            )
        )

        ep_detail = EpisodeDetail(
            id=f"{anime_id}-{ep_num_int}",
            anime_id=anime_id,
            episode_number=float(episode_number),
            title=f"Episode {ep_num_int}",
            subtitles=subtitles,
            servers=servers,
            downloads=downloads,
            prev_episode=float(ep_num_int - 1) if ep_num_int > 1 else None,
            next_episode=float(ep_num_int + 1)
        )

        self.storage.save_episode_detail(ep_detail)
        return ep_detail

    def crawl_series(
        self,
        id_or_url: str,
        max_episodes: Optional[int] = None,
        resolve_streams: bool = True
    ) -> SeriesDetail:
        """
        Crawls and stores a series along with its episode playback details in SQLite database.
        """
        series = self.get_series_detail(id_or_url)
        target_episodes = series.episodes
        if max_episodes:
            target_episodes = target_episodes[:max_episodes]

        for ep in target_episodes:
            if resolve_streams:
                try:
                    self.get_episode_detail(series.id, ep.episode_number)
                except Exception:
                    pass

        return series
