"""Core Scraper for HDHub4u."""

import re
import logging
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from common.ui import clean_text
from .http_client import HDHub4uHttpClient
from .config import SEARCH_API_URL
from .models import (
    HDHub4uSearchResult,
    HDHub4uDetail,
    HDHub4uDownloadLink,
    HDHub4uEpisode,
)

logger = logging.getLogger("hdhub4u.scraper")


class HDHub4uScraper:
    """Scraper implementation for HDHub4u (Dual Audio, 4K, 1080p Movies & Web Series)."""

    def __init__(self, http_client: Optional[HDHub4uHttpClient] = None):
        self.http = http_client or HDHub4uHttpClient()

    def _identify_provider(self, url: str) -> str:
        """Derive friendly provider name."""
        netloc = urlparse(url).netloc.lower()
        if "hubdrive" in netloc:
            return "HubDrive"
        if "hubcloud" in netloc:
            return "HubCloud"
        if "hubcdn" in netloc:
            return "HubCDN"
        if "pixeldrain" in netloc:
            return "PixelDrain"
        if "drive" in netloc:
            return "GDrive"
        return netloc or "FastDownload"

    def _extract_quality_size(self, text: str):
        """Extract resolution and file size from link anchor text."""
        quality = None
        size = None

        if "4k" in text.lower() or "2160p" in text.lower():
            quality = "4K 2160p"
        elif "1080p" in text.lower():
            quality = "1080p"
        elif "720p" in text.lower():
            quality = "720p"
        elif "480p" in text.lower():
            quality = "480p"

        size_match = re.search(r"\[([\d.]+\s*(?:GB|MB))\]", text, re.IGNORECASE)
        if size_match:
            size = size_match.group(1)

        return quality, size

    def search(self, query: str, page: int = 1, limit: int = 15) -> List[HDHub4uSearchResult]:
        """Search titles using HDHub4u Typesense API cluster."""
        params = {
            "q": query,
            "query_by": "post_title,category,stars,director,imdb_id",
            "query_by_weights": "4,2,2,2,4",
            "sort_by": "sort_by_date:desc",
            "limit": limit,
            "page": page,
        }
        resp = self.http.get(SEARCH_API_URL, params=params)
        data = resp.json()

        results: List[HDHub4uSearchResult] = []
        for hit in data.get("hits", []):
            doc = hit.get("document", {})
            title = clean_text(doc.get("post_title", ""))
            permalink = doc.get("permalink", "")
            thumb = doc.get("post_thumbnail")

            if not title or not permalink:
                continue

            path = urlparse(permalink).path
            slug = path.strip("/").split("/")[-1]
            media_type = "series" if "series" in path or "season" in title.lower() else "movie"

            quality_tag = None
            if "4k" in title.lower():
                quality_tag = "4K"
            elif "1080p" in title.lower():
                quality_tag = "1080p"
            elif "720p" in title.lower():
                quality_tag = "720p"

            results.append(
                HDHub4uSearchResult(
                    title=title,
                    link=path,
                    slug=slug,
                    poster=thumb,
                    media_type=media_type,
                    quality_tag=quality_tag,
                )
            )
        return results

    def get_catalog(self, category: str = "bollywood-movies", page: int = 1) -> List[HDHub4uSearchResult]:
        """Browse category: 'bollywood-movies', 'hollywood-movies', 'hindi-dubbed', 'category/web-series'."""
        clean_cat = category.strip("/")
        if clean_cat.startswith("category/"):
            path = f"/{clean_cat}/"
        else:
            path = f"/category/{clean_cat}/"

        if page > 1:
            path = f"{path}page/{page}/"

        resp = self.http.get(path)
        soup = BeautifulSoup(resp.text, "html.parser")

        results: List[HDHub4uSearchResult] = []
        for li in soup.select("ul.recent-movies > li, li.recent-movies"):
            a = li.select_one("a")
            if not a:
                continue

            href = a.get("href", "")
            img = li.select_one("img")
            poster = img.get("src") or img.get("data-src") if img else None

            title_el = li.select_one("p, h2, h3, .entry-title")
            title = clean_text(title_el.text if title_el else a.get("title", ""))
            if not title:
                continue

            slug = href.strip("/").split("/")[-1]
            media_type = "series" if "series" in href or "season" in title.lower() else "movie"

            results.append(
                HDHub4uSearchResult(
                    title=title,
                    link=href,
                    slug=slug,
                    poster=poster,
                    media_type=media_type,
                )
            )
        return results

    def get_detail(self, link_or_slug: str) -> HDHub4uDetail:
        """Fetch complete movie or series detail with download & stream links."""
        if link_or_slug.startswith("http"):
            url = link_or_slug
        elif link_or_slug.startswith("/"):
            url = f"{self.http.base_url}{link_or_slug}"
        else:
            url = f"{self.http.base_url}/{link_or_slug}/"

        resp = self.http.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        title_el = soup.select_one("h1.entry-title, h1")
        title = clean_text(title_el.text if title_el else link_or_slug)

        poster_el = soup.select_one("div.entry-content img, article img")
        poster = poster_el.get("src") if poster_el else None

        desc_el = soup.select_one("div.entry-content p, .synopsis")
        synopsis = desc_el.text.strip() if desc_el else None

        slug = url.strip("/").split("/")[-1]
        media_type = "series" if "series" in url or "season" in title.lower() else "movie"

        # Find all download links (HubDrive, HubCloud, HubCDN, PixelDrain, GDrive)
        movie_links: List[HDHub4uDownloadLink] = []
        episodes_map = {}

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = a.get_text(strip=True)

            if not href.startswith("http"):
                continue

            if any(skip in href.lower() for skip in ["how-to", "disclaimer", "request", "telegram", "join", "hdhub4u."]):
                continue

            if not any(k in href.lower() for k in ["hubdrive", "hubcloud", "hubcdn", "pixeldrain", "driveleech", "gdflix", "file"]):
                continue

            quality, size = self._extract_quality_size(text)
            provider = self._identify_provider(href)

            link_obj = HDHub4uDownloadLink(
                label=text or provider,
                url=href,
                quality=quality,
                size=size,
                provider=provider,
            )

            # Check if this is an episode link (e.g. 'Episode 1', 'EP-01', 'Drive [Ep 1]')
            ep_match = re.search(r"(?:ep|episode)[\s\-_]*0*(\d+)", text, re.IGNORECASE)
            if ep_match and media_type == "series":
                ep_num = int(ep_match.group(1))
                if ep_num not in episodes_map:
                    episodes_map[ep_num] = []
                episodes_map[ep_num].append(link_obj)
            else:
                movie_links.append(link_obj)

        episodes = [
            HDHub4uEpisode(
                episode_num=ep_num,
                title=f"Episode {ep_num}",
                links=links,
            )
            for ep_num, links in sorted(episodes_map.items())
        ]

        return HDHub4uDetail(
            title=title,
            slug=slug,
            link=url,
            media_type=media_type,
            poster=poster,
            synopsis=synopsis,
            movie_links=movie_links,
            episodes=episodes,
        )

    def close(self):
        self.http.close()
