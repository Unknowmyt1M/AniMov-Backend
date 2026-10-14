"""Core Scraper for ReAnime (reanime.to) SvelteKit Architecture."""

import re
import json
import logging
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup

from .config import BASE_URL
from .http_client import ReAnimeHttpClient
from .models import (
    ReAnimeSearchResult,
    ReAnimeEpisode,
    ReAnimeStreamResult,
    ReAnimeSeriesDetail,
)
from .storage import ReAnimeStorage

logger = logging.getLogger("reanime.scraper")


class ReAnimeScraper:
    """Production scraper for ReAnime (reanime.to)."""

    def __init__(
        self,
        http_client: Optional[ReAnimeHttpClient] = None,
        storage: Optional[ReAnimeStorage] = None,
    ):
        self.client = http_client or ReAnimeHttpClient()
        self.storage = storage or ReAnimeStorage()

    def search(self, query: str) -> List[ReAnimeSearchResult]:
        """Search ReAnime by anime title or keyword."""
        url = f"{BASE_URL}/search"
        response = self.client.get(url, params={"q": query})
        soup = BeautifulSoup(response.text, "html.parser")

        results: List[ReAnimeSearchResult] = []
        seen_slugs = set()

        for a in soup.find_all("a", href=re.compile(r"^/anime/[a-zA-Z0-9_-]+$")):
            href = a.get("href", "")
            slug = href.replace("/anime/", "").strip("/")
            if not slug or slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            img = a.find("img")
            poster = img.get("src") if img else None

            # Parse metadata badges / card text
            text_parts = [p.strip() for p in a.get_text(separator="|").split("|") if p.strip()]
            
            # 1. Score
            score = None
            for part in text_parts:
                if re.match(r"^\d+\.\d+$", part):
                    score = part
                    break

            # 2. Anime Type
            anime_type = "TV Series"
            for part in text_parts:
                up = part.upper()
                if up in ("TV", "SERIES"):
                    anime_type = "TV Series"
                    break
                elif up in ("MOVIE", "FILM"):
                    anime_type = "Anime Movie"
                    break
                elif up in ("ONA", "OVA", "SPECIAL"):
                    anime_type = up
                    break

            # 3. Episodes
            episodes = None
            for part in text_parts:
                if re.match(r"^\d+(?:/\d+)+$", part):
                    # Usually like sub/dub/total or total, e.g. 13/13/13
                    nums = [int(n) for n in part.split("/") if n.isdigit()]
                    max_ep = max(nums) if nums else 1
                    episodes = f"{max_ep} eps"
                    break
            if not episodes:
                episodes = "1 Ep (Movie)" if anime_type == "Anime Movie" else "Ongoing"

            # 4. Duration
            duration = None
            for part in text_parts:
                m_dur = re.search(r'(\d+\s*(?:m|h)(?:\s*\d+m)?)', part, re.I)
                if m_dur:
                    dur_val = m_dur.group(1)
                    duration = f"{dur_val} / ep" if anime_type != "Anime Movie" else dur_val
                    break
            if not duration:
                duration = "Feature Film" if anime_type == "Anime Movie" else "~24m / ep"

            # 5. Title
            title = None
            if img and img.get("alt") and img.get("alt").strip():
                title = img.get("alt").strip()

            if not title:
                for part in text_parts:
                    if re.match(r"^\d+$", part) or re.match(r"^\d+\.\d+$", part) or re.match(r"^\d+(?:/\d+)+$", part):
                        continue
                    if part.upper() in ("TV", "MOVIE", "ONA", "OVA", "SPECIAL", "DUB", "SUB", "R-17+", "PG-13", "R", "G"):
                        continue
                    if re.match(r"^•?\s*\d+\s*(?:m|h)$", part):
                        continue
                    if len(part) > 2:
                        title = part
                        break

            if not title:
                title = slug.replace("-", " ").title()

            results.append(
                ReAnimeSearchResult(
                    slug=slug,
                    title=title,
                    poster=poster,
                    anime_type=anime_type,
                    episodes=episodes,
                    duration=duration,
                    score=score,
                    link=f"{BASE_URL}{href}",
                )
            )

        logger.info(f"ReAnime search for '{query}' returned {len(results)} items.")
        return results

    def get_series_detail(
        self,
        slug: str,
        use_cache: bool = True,
        max_age_seconds: Optional[int] = 86400 * 7,
    ) -> Optional[ReAnimeSeriesDetail]:
        """Fetch rich series metadata and episode roster from ReAnime."""
        slug = slug.strip().strip("/").split("/")[-1]
        if use_cache:
            cached = self.storage.get_series(slug, max_age_seconds=max_age_seconds)
            if cached and cached.episodes:
                return cached

        # Step 1: Fetch anime overview page
        url = f"{BASE_URL}/anime/{slug}"
        response = self.client.get(url)
        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        h1 = soup.find("h1")
        is_404 = (
            response.status_code == 404
            or (h1 and h1.get_text(strip=True) == "404")
            or (soup.title and "not found" in soup.title.get_text(strip=True).lower())
        )

        if is_404:
            logger.info(f"Direct slug '{slug}' not found on ReAnime, searching candidates...")
            candidates = self.search(slug.replace("-", " "))
            matched_slug = None
            slug_clean = slug.lower()
            for cand in candidates:
                cand_clean = cand.slug.lower()
                if cand_clean == slug_clean or cand_clean.startswith(f"{slug_clean}-") or cand_clean.rsplit("-", 1)[0] == slug_clean:
                    matched_slug = cand.slug
                    break
            if not matched_slug and candidates:
                cand_words = set(candidates[0].slug.split("-"))
                slug_words = set(slug.split("-"))
                if slug_words.issubset(cand_words):
                    matched_slug = candidates[0].slug

            if matched_slug and matched_slug != slug:
                logger.info(f"Resolved slug '{slug}' -> '{matched_slug}'")
                slug = matched_slug
                if use_cache:
                    cached = self.storage.get_series(slug, max_age_seconds=max_age_seconds)
                    if cached and cached.episodes:
                        return cached
                url = f"{BASE_URL}/anime/{slug}"
                response = self.client.get(url)
                html = response.text
                soup = BeautifulSoup(html, "html.parser")
                h1 = soup.find("h1")
                is_404 = (
                    response.status_code == 404
                    or (h1 and h1.get_text(strip=True) == "404")
                    or (soup.title and "not found" in soup.title.get_text(strip=True).lower())
                )

        if is_404:
            logger.error(f"Failed to find anime on ReAnime: {slug}")
            return None

        title = h1.get_text(strip=True) if h1 else slug.replace("-", " ").title()

        # Banner and Cover images
        banner = None
        banner_img = soup.find("img", alt=re.compile(r"banner", re.I))
        if banner_img and banner_img.get("src"):
            banner = banner_img["src"]
        elif re.search(r'https?://[^\s"\']+/media/anime/banner/[^\s"\']+', html):
            m = re.search(r'(https?://[^\s"\']+/media/anime/banner/[^\s"\']+)', html)
            if m:
                banner = m.group(1)

        poster = None
        poster_img = soup.find("img", {"src": re.compile(r"/media/anime/cover/")})
        if poster_img and poster_img.get("src"):
            poster = poster_img["src"]
        else:
            m = re.search(r'(https?://[^\s"\']+/media/anime/cover/[^\s"\']+)', html)
            if m:
                poster = m.group(1)

        # Synopsis
        synopsis = None
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) > 60:
                synopsis = text
                break

        # Parse SvelteKit structured state data
        english_title = None
        romaji_title = None
        native_title = None
        anilist_id = None
        mal_id = None
        genres: List[str] = []
        average_score = None
        anime_status = None
        season = None
        season_year = None
        total_episodes = 0

        # Extract AniList ID
        m_ani = re.search(r'anilist_id:(\d+)', html) or re.search(r'/bx(\d+)-', html) or re.search(r'/anime/banner/(\d+)-', html)
        if m_ani:
            try:
                anilist_id = int(m_ani.group(1))
            except ValueError:
                pass

        # Extract MAL ID
        m_mal = re.search(r'mal_id:(\d+)', html) or re.search(r'myanimelist\.net/anime/(\d+)', html)
        if m_mal:
            try:
                mal_id = int(m_mal.group(1))
            except ValueError:
                pass

        # Extract genres
        m_genres = re.search(r'genres:\[(.*?)\]', html)
        if m_genres:
            raw_genres = re.findall(r'"([^"]+)"', m_genres.group(1))
            genres = [g.strip() for g in raw_genres if g.strip()]

        # Extract Score
        m_score = re.search(r'average_score:(\d+)', html)
        if m_score:
            try:
                average_score = int(m_score.group(1))
            except ValueError:
                pass

        # Extract Status
        m_status = re.search(r'status:"([^"]+)"', html)
        if m_status:
            anime_status = m_status.group(1)

        # Extract Season & Year
        m_season = re.search(r'season:"([^"]+)"', html)
        if m_season:
            season = m_season.group(1)
        m_year = re.search(r'season_year:(\d+)', html)
        if m_year:
            try:
                season_year = int(m_year.group(1))
            except ValueError:
                pass

        # Extract Total Episodes
        m_ep_total = re.search(r'episodes_total:(\d+)', html)
        if m_ep_total:
            try:
                total_episodes = int(m_ep_total.group(1))
            except ValueError:
                pass

        # Step 2: Fetch watch page to parse the complete episode roster
        episodes = self._fetch_episodes_from_watch_page(slug)
        if not episodes and total_episodes > 0:
            # Fallback to generated episode list
            episodes = [
                ReAnimeEpisode(
                    id=f"ep-{i}",
                    episode_num=i,
                    title=f"Episode {i}",
                )
                for i in range(1, total_episodes + 1)
            ]

        if not total_episodes and episodes:
            total_episodes = len(episodes)

        detail = ReAnimeSeriesDetail(
            slug=slug,
            title=title,
            english_title=english_title,
            native_title=native_title,
            romaji_title=romaji_title,
            anilist_id=anilist_id,
            mal_id=mal_id,
            poster=poster,
            banner=banner,
            synopsis=synopsis,
            status=anime_status,
            season=season,
            season_year=season_year,
            genres=genres,
            average_score=average_score,
            total_episodes=total_episodes,
            episodes=episodes,
        )

        self.storage.save_series(detail)
        return detail

    def _fetch_episodes_from_watch_page(self, slug: str) -> List[ReAnimeEpisode]:
        """Fetch watch page and parse SSR episode card list."""
        watch_url = f"{BASE_URL}/watch/{slug}"
        try:
            response = self.client.get(watch_url)
            soup = BeautifulSoup(response.text, "html.parser")
            ep_cards = soup.find_all("a", href=lambda h: h and "/watch/" in h and "?ep=" in h)
            
            episodes: List[ReAnimeEpisode] = []
            seen_ep_nums = set()

            for card in ep_cards:
                ep_attr = card.get("data-episode")
                if ep_attr and ep_attr.isdigit():
                    ep_num = int(ep_attr)
                else:
                    # Parse from href ?ep=X
                    href = card.get("href", "")
                    m = re.search(r"\?ep=(\d+)", href)
                    if m:
                        ep_num = int(m.group(1))
                    else:
                        continue

                if ep_num in seen_ep_nums:
                    continue
                seen_ep_nums.add(ep_num)

                title_elem = card.find(class_=re.compile(r"ep-title"))
                ep_title = title_elem.get_text(strip=True) if title_elem else f"Episode {ep_num}"

                is_sub = bool(card.find(class_=re.compile(r"\bsub\b")))
                is_dub = bool(card.find(class_=re.compile(r"\bdub\b")))
                is_filler = bool(card.find(class_=re.compile(r"\bfiller\b")))
                is_recap = bool(card.find(class_=re.compile(r"\brecap\b")))

                aired_elem = card.find(class_=re.compile(r"ep-aired"))
                aired_at = aired_elem.get_text(strip=True) if aired_elem else None

                episodes.append(
                    ReAnimeEpisode(
                        id=f"ep-{ep_num}",
                        episode_num=ep_num,
                        title=ep_title,
                        is_subbed=is_sub,
                        is_dubbed=is_dub,
                        is_filler=is_filler,
                        is_recap=is_recap,
                        aired_at=aired_at,
                        playable=True,
                    )
                )

            episodes.sort(key=lambda x: x.episode_num)
            return episodes
        except Exception as e:
            logger.warning(f"Failed to fetch episodes from watch page for {slug}: {e}")
            return []

    def get_episode_stream(self, slug: str, episode_num: int, use_cache: bool = True) -> ReAnimeStreamResult:
        """Extract streaming player / video embed for a given episode."""
        if use_cache:
            cached = self.storage.get_stream(slug, episode_num)
            if cached and cached.embed_url:
                return cached

        watch_url = f"{BASE_URL}/watch/{slug}?ep={episode_num}"
        response = self.client.get(watch_url)
        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        # Check for direct iframe
        embed_url = None
        iframe = soup.find("iframe")
        if iframe and iframe.get("src"):
            embed_url = iframe["src"]

        # Check for embed URL in script or SvelteKit state
        if not embed_url:
            m_embed = re.search(
                r'(https?://(?:megacloud|flixcloud|rabbitstream|streamtape|dood|vidcloud|rapid-cloud)[^\s"\'<>]+)',
                html,
            )
            if m_embed:
                embed_url = m_embed.group(1)

        # Check for direct m3u8
        if not embed_url:
            m_m3u8 = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
            if m_m3u8:
                embed_url = m_m3u8.group(1)

        if embed_url:
            res = ReAnimeStreamResult(
                slug=slug,
                episode_num=episode_num,
                embed_url=embed_url,
                status="available",
            )
        else:
            res = ReAnimeStreamResult(
                slug=slug,
                episode_num=episode_num,
                embed_url=None,
                status="upstream_sources_pending",
                message="No active streaming server provided by ReAnime for this episode at this moment.",
            )

        self.storage.save_stream(res)
        return res

    def close(self):
        """Clean up HTTP client session."""
        self.client.close()
