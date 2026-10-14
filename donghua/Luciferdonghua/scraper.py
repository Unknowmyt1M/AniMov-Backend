"""
Core Scraper Engine for Lucifer Donghua (https://luciferdonghua.in).
Exhaustive Donghua extraction:
- Metadata (Studios, Directors, Producers, Ratings, Followers, Tags)
- Character & Voice Actors roster
- Episode listings with release dates & batch ranges (04 & 05 [4K])
- Multi-server streaming mirrors (Rumble, Dailymotion, VidHide, OK.ru)
- Direct download links
"""

import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup

from .config import (
    PRIMARY_DOMAIN,
    DEFAULT_CONCURRENCY,
)
from .http_client import LuciferHttpClient
from .models import (
    LuciferDonghuaDetail,
    LuciferEpisodeDetail,
    LuciferEpisodeListItem,
    LuciferStreamServer,
    LuciferDownloadOption,
    LuciferCatalogCard,
    CharacterItem,
)
from .episode_parser import (
    parse_lucifer_episode_number,
    resolve_episode_title_and_number,
)
from .server_resolver import (
    parse_mirror_options,
    extract_active_embed,
    extract_download_links,
)
from .storage import LuciferStorage
from .sniffer import LuciferStreamSniffer


class LuciferDonghuaScraper:
    """Production-grade scraper engine for luciferdonghua.in."""

    def __init__(
        self,
        base_url: str = PRIMARY_DOMAIN,
        storage: Optional[LuciferStorage] = None,
        concurrency: int = DEFAULT_CONCURRENCY,
    ):
        self.base_url = base_url.rstrip("/")
        self.client = LuciferHttpClient(primary_domain=self.base_url)
        self.storage = storage or LuciferStorage()
        self.concurrency = concurrency
        self.sniffer = LuciferStreamSniffer()

    def _resolve_series_url(self, slug_or_url: str) -> str:
        """Resolves series slug or full URL to canonical /anime/{slug}/ route."""
        if slug_or_url.startswith("http://") or slug_or_url.startswith("https://"):
            return slug_or_url

        cleaned = slug_or_url.strip("/ ")
        return f"{self.base_url}/anime/{cleaned}/"

    def search(self, query: str) -> List[LuciferCatalogCard]:
        """Searches Lucifer Donghua and returns matching series cards."""
        encoded = urllib.parse.quote_plus(query)
        search_url = f"{self.base_url}/?s={encoded}"
        html = self.client.get(search_url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        cards: List[LuciferCatalogCard] = []

        for item in soup.select("article.bs, .animposx"):
            a_tag = item.find("a", href=True)
            if not a_tag:
                continue

            url = a_tag["href"]
            if "-episode-" in url:
                continue

            title = a_tag.get("title") or item.find(["h2", "h3"])
            title_text = title.text.strip() if hasattr(title, "text") else str(title).strip()

            img_tag = item.find("img")
            poster_url = ""
            if img_tag:
                poster_url = img_tag.get("data-src") or img_tag.get("src") or ""

            ep_tag = item.select_one(".epx, .bt .epx")
            latest_ep = ep_tag.text.strip() if ep_tag else None

            type_tag = item.select_one(".typez")
            media_type = type_tag.text.strip() if type_tag else "ONA"

            parsed = urllib.parse.urlparse(url)
            slug = parsed.path.strip("/").split("/")[-1]

            cards.append(
                LuciferCatalogCard(
                    title=title_text,
                    slug=slug,
                    url=url,
                    poster_url=poster_url,
                    type=media_type,
                    status=None,
                    latest_episode=latest_ep,
                )
            )

        return cards

    def get_catalog_page(self, page: int = 1) -> List[LuciferCatalogCard]:
        """Retrieves a page of series from /anime/?page=N."""
        cat_url = f"{self.base_url}/anime/?page={page}" if page > 1 else f"{self.base_url}/anime/"
        html = self.client.get(cat_url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        cards: List[LuciferCatalogCard] = []

        for item in soup.select("article.bs, .animposx"):
            a_tag = item.find("a", href=True)
            if not a_tag:
                continue

            url = a_tag["href"]
            title_elem = item.find(["h2", "h3"]) or item.select_one(".tt")
            title = a_tag.get("title") or (title_elem.text.strip() if title_elem else "")

            img_tag = item.find("img")
            poster_url = ""
            if img_tag:
                poster_url = img_tag.get("data-src") or img_tag.get("src") or ""

            ep_tag = item.select_one(".epx, .bt .epx")
            latest_ep = ep_tag.text.strip() if ep_tag else None

            type_tag = item.select_one(".typez")
            media_type = type_tag.text.strip() if type_tag else "ONA"

            parsed = urllib.parse.urlparse(url)
            slug = parsed.path.strip("/").split("/")[-1]

            cards.append(
                LuciferCatalogCard(
                    title=title,
                    slug=slug,
                    url=url,
                    poster_url=poster_url,
                    type=media_type,
                    latest_episode=latest_ep,
                )
            )

        return cards

    def get_donghua_details(self, series_url_or_slug: str, refresh: bool = False) -> Optional[LuciferDonghuaDetail]:
        """
        Parses exhaustive Donghua series metadata, character list, and episode tables.
        """
        target_url = self._resolve_series_url(series_url_or_slug)
        html = self.client.get(target_url, refresh=refresh)
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")

        # 1. Title & Alternate Titles
        title_el = soup.find("h1", class_="entry-title") or soup.find("h1")
        title = title_el.text.strip() if title_el else "Unknown Title"

        alter_el = soup.find("span", class_="alter")
        alt_titles = alter_el.text.strip() if alter_el else None

        parsed_url = urllib.parse.urlparse(target_url)
        slug = parsed_url.path.strip("/").split("/")[-1]

        # 2. Rating & Followers
        rating_el = soup.find("div", class_="rating") or soup.find("div", class_="num")
        rating = None
        if rating_el:
            clean_rating = re.search(r"\d+(?:\.\d+)?", rating_el.text)
            if clean_rating:
                rating = clean_rating.group(0)

        followers_el = soup.find("div", class_="bmc") or soup.find(string=re.compile(r"Followed\s+\d+", re.IGNORECASE))
        followers = followers_el.text.strip() if hasattr(followers_el, "text") else (str(followers_el).strip() if followers_el else None)

        # 3. Poster Image
        img_tag = soup.select_one(".thumb img, .wp-post-image, .bigcontent img")
        poster_url = None
        if img_tag:
            poster_url = img_tag.get("data-src") or img_tag.get("src")
            if poster_url and poster_url.startswith("//"):
                poster_url = "https:" + poster_url

        # 4. Info Content key-values
        meta_dict: Dict[str, str] = {}
        info_content = soup.find("div", class_="info-content")
        if info_content:
            for span in info_content.find_all("span"):
                span_text = span.get_text(" ", strip=True)
                if ":" in span_text:
                    k, v = span_text.split(":", 1)
                    meta_dict[k.strip().lower()] = v.strip()

        # Extract producers from links inside info-content if available
        producers: List[str] = []
        if info_content:
            for a in info_content.find_all("a", href=True):
                if "/producer/" in a["href"]:
                    p_name = a.text.strip()
                    if p_name and p_name not in producers:
                        producers.append(p_name)

        # 5. Genres
        genres: List[str] = []
        bcontent = soup.find("div", class_="bigcontent") or soup.find("div", class_="infox")
        if bcontent:
            for a in bcontent.find_all("a", href=True):
                if "/genres/" in a["href"]:
                    g_text = a.text.strip()
                    if g_text and g_text.lower() != "genres" and g_text not in genres:
                        genres.append(g_text)

        # 6. Tags
        tags: List[str] = []
        for a in soup.find_all("a", href=True):
            if "/tag/" in a["href"]:
                t_text = a.text.strip()
                if t_text and t_text not in tags:
                    tags.append(t_text)

        # 7. Synopsis
        synopsis = None
        entry_content = soup.find("div", class_="entry-content")
        if entry_content:
            synopsis = entry_content.get_text("\n", strip=True)

        # 8. Characters & Voice Actors
        characters: List[CharacterItem] = []
        for char_box in soup.select(".characters .char-item, .vactor li, .characters-list li"):
            char_name = char_box.find(class_=re.compile(r"name|char", re.IGNORECASE))
            char_role = char_box.find(class_=re.compile(r"role|sub", re.IGNORECASE))
            char_img = char_box.find("img")

            if char_name:
                characters.append(
                    CharacterItem(
                        name=char_name.text.strip(),
                        role=char_role.text.strip() if char_role else "Supporting",
                        image_url=char_img.get("src") if char_img else None,
                    )
                )

        # 9. Episode List parsing
        episodes: List[LuciferEpisodeListItem] = []
        eplister = soup.find("div", class_="eplister") or soup.find("ul", class_="clstyle")

        if eplister:
            li_items = eplister.find_all("li")
            for idx, li in enumerate(li_items, start=1):
                a_tag = li.find("a", href=True)
                if not a_tag:
                    continue

                ep_url = a_tag["href"]
                num_elem = li.find(class_="epl-num")
                title_elem = li.find(class_="epl-title")
                sub_elem = li.find(class_="epl-sub")
                date_elem = li.find(class_="epl-date")

                raw_num = num_elem.text.strip() if num_elem else ""
                raw_title = title_elem.text.strip() if title_elem else a_tag.text.strip()
                sub_type = sub_elem.text.strip() if sub_elem else "Sub"
                rel_date = date_elem.text.strip() if date_elem else None

                ep_num, clean_title, quality = resolve_episode_title_and_number(
                    raw_num, raw_title, index=idx
                )

                episodes.append(
                    LuciferEpisodeListItem(
                        episode_number=ep_num,
                        raw_number_text=raw_num,
                        title=clean_title,
                        sub_type=sub_type,
                        quality_tag=quality,
                        release_date=rel_date,
                        url=ep_url,
                    )
                )

        # Sort naturally ascending by episode number (1 -> N)
        episodes.sort(key=lambda x: x.episode_number)

        first_episode_url = episodes[0].url if episodes else None
        latest_episode_url = episodes[-1].url if episodes else None

        detail = LuciferDonghuaDetail(
            title=title,
            alternative_titles=alt_titles,
            slug=slug,
            rating=rating,
            followers=followers,
            poster_url=poster_url,
            status=meta_dict.get("status"),
            studio=meta_dict.get("studio"),
            released_year=meta_dict.get("released"),
            duration=meta_dict.get("duration"),
            country=meta_dict.get("country", "China"),
            type=meta_dict.get("type", "ONA"),
            total_episodes_expected=meta_dict.get("episodes"),
            fansub=meta_dict.get("fansub"),
            director=meta_dict.get("director"),
            producers=producers,
            posted_by=meta_dict.get("posted by"),
            site_released_on=meta_dict.get("released on"),
            site_updated_on=meta_dict.get("updated on"),
            genres=genres,
            tags=tags,
            synopsis=synopsis,
            characters=characters,
            first_episode_url=first_episode_url,
            latest_episode_url=latest_episode_url,
            total_scraped_episodes=len(episodes),
            episodes=episodes,
            source_url=target_url,
        )

        return detail

    def get_episode_details(
        self,
        episode_url: str,
        resolve_embeds: bool = True,
        run_sniffer: bool = False,
        refresh: bool = False,
    ) -> Optional[LuciferEpisodeDetail]:
        """
        Parses episode playback details:
        - Title, published date, views, uploader, parent series breadcrumb
        - Default player embed source
        - Server mirrors (Dailymotion, Rumble, VidHide, OK.ru)
        - Direct download links
        """
        html = self.client.get(episode_url, refresh=refresh)
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")

        # 1. Title & Number
        title_elem = soup.find("h1", class_="entry-title") or soup.find("h1")
        ep_title = title_elem.text.strip() if title_elem else "Episode"
        ep_num = parse_lucifer_episode_number(ep_title)

        # 2. Release Date from meta
        pub_meta = soup.find("meta", property="article:published_time")
        release_date = pub_meta["content"] if pub_meta and pub_meta.get("content") else None
        if not release_date:
            date_match = re.search(r"Released\s+on\s*:?\s*([^·\n]+)", soup.text, re.IGNORECASE)
            if date_match:
                release_date = date_match.group(1).strip()

        # 3. Views
        views = None
        views_match = re.search(r"\b(\d+\s*views)\b", soup.text, re.IGNORECASE)
        if views_match:
            views = views_match.group(1)

        # 4. Author / Uploader
        author_el = soup.select_one(".author a, .posted-by a, .year a")
        posted_by = author_el.text.strip() if author_el else None

        # 5. Parent Series Breadcrumb (always item 1)
        series_title = None
        series_url = None
        breadcrumbs = soup.select(".ts-breadcrumb a, .breadcrumb a")
        if len(breadcrumbs) >= 2:
            series_title = breadcrumbs[1].text.strip()
            series_url = breadcrumbs[1].get("href")

        # 6. Prev / Next Navigation
        prev_url = None
        next_url = None
        for a in soup.select(".navep a, .nvs a"):
            txt = a.text.lower()
            if "prev" in txt:
                prev_url = a.get("href")
            elif "next" in txt:
                next_url = a.get("href")

        # 7. Default player embed from #pembed
        default_embed = extract_active_embed(soup)

        # 8. Server Mirrors
        servers = parse_mirror_options(soup, base_url=self.base_url)

        # Assign default embed to the first server if missing
        if servers and default_embed and not servers[0].embed_url:
            servers[0].embed_url = default_embed

        # If resolve_embeds is requested, fetch /v/{n}/ to resolve clean embeds for each mirror
        if resolve_embeds and len(servers) > 1:
            for s in servers[1:]:
                if s.server_url and not s.embed_url:
                    server_html = self.client.get(s.server_url, refresh=refresh)
                    if server_html:
                        srv_soup = BeautifulSoup(server_html, "html.parser")
                        s.embed_url = extract_active_embed(srv_soup)

        # 9. Download Links
        downloads = extract_download_links(soup)

        # 10. Optional Stream Sniffer
        if run_sniffer:
            target_embed = default_embed or (servers[0].embed_url if servers else None)
            if target_embed:
                captured = self.sniffer.sniff_embed_sync(target_embed)
                if captured and servers:
                    servers[0].direct_stream_url = captured[0][0]

        detail = LuciferEpisodeDetail(
            episode_title=ep_title,
            episode_number=ep_num,
            release_date=release_date,
            views=views,
            posted_by=posted_by,
            series_title=series_title,
            series_url=series_url,
            prev_episode_url=prev_url,
            next_episode_url=next_url,
            default_embed=default_embed,
            servers=servers,
            downloads=downloads,
            source_url=episode_url,
        )

        return detail

    def crawl_series(
        self,
        series_slug_or_url: str,
        scrape_episodes: bool = True,
        max_episodes: Optional[int] = None,
        refresh: bool = False,
    ) -> Optional[LuciferDonghuaDetail]:
        """Crawls a Lucifer Donghua series and populates SQLite database."""
        detail = self.get_donghua_details(series_slug_or_url, refresh=refresh)
        if not detail:
            return None

        self.storage.save_donghua(detail, state="detail_parsed")

        if not scrape_episodes or not detail.episodes:
            return detail

        target_episodes = detail.episodes
        if max_episodes:
            target_episodes = target_episodes[:max_episodes]

        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            future_to_ep = {
                executor.submit(self.get_episode_details, ep.url, False, False, refresh): ep
                for ep in target_episodes
            }

            for future in as_completed(future_to_ep):
                ep_item = future_to_ep[future]
                try:
                    ep_detail = future.result()
                    if ep_detail:
                        self.storage.save_episode_detail(ep_detail, detail.slug, state="done")
                    else:
                        self.storage.mark_episode_failed(ep_item.url)
                except Exception:
                    self.storage.mark_episode_failed(ep_item.url)

        return self.storage.get_donghua(detail.slug) or detail
