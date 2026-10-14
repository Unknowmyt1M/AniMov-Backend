"""
Robust episode title parser and ascending order resolver for AnimeKhor.
"""
import re
from typing import List, Optional
from bs4 import BeautifulSoup
from .models import EpisodeSummary


class EpisodeParser:
    @staticmethod
    def extract_episode_number(text: str, url: str = "") -> float:
        """
        Extract numerical episode value from text or URL slug.
        Handles: '160', 'Episode 160', 'Part 2', 'Episode 217-243', 'Ep 12.5'.
        """
        clean_text = text.strip()

        # Handle 'Episode 217-243' or '217-243'
        range_match = re.search(r'(?:ep|episode)?\s*(\d+)\s*(?:-|to|&)\s*(\d+)', clean_text, re.IGNORECASE)
        if range_match:
            try:
                return float(range_match.group(1))
            except ValueError:
                pass

        # Handle 'Part 2'
        part_match = re.search(r'\bpart\s*(\d+(?:\.\d+)?)\b', clean_text, re.IGNORECASE)
        if part_match:
            try:
                return float(part_match.group(1))
            except ValueError:
                pass

        # Handle 'Episode 160' or 'Ep 160'
        ep_match = re.search(r'(?:ep|episode|e)\s*(\d+(?:\.\d+)?)', clean_text, re.IGNORECASE)
        if ep_match:
            try:
                return float(ep_match.group(1))
            except ValueError:
                pass

        # Handle pure digits like '160'
        if clean_text.isdigit():
            return float(clean_text)

        # Fallback to URL inspection
        if url:
            url_match = re.search(r'episode-(\d+(?:\.\d+)?)', url, re.IGNORECASE)
            if url_match:
                try:
                    return float(url_match.group(1))
                except ValueError:
                    pass

        # Any standalone number
        standalone = re.findall(r'\d+(?:\.\d+)?', clean_text)
        if standalone:
            try:
                return float(standalone[0])
            except ValueError:
                pass

        return 0.0

    @classmethod
    def parse_episode_list(cls, soup: BeautifulSoup) -> List[EpisodeSummary]:
        """
        Parses episode elements from .eplister or .episodelst, returning sorted in ascending order.
        """
        episodes: List[EpisodeSummary] = []
        raw_items = soup.select("div.eplister ul li, div.episodelst ul li, ul.clstyle li")

        for item in raw_items:
            a_tag = item.select_one("a")
            if not a_tag or not a_tag.get("href"):
                continue

            url = a_tag["href"].strip()
            num_elem = item.select_one(".epl-num")
            title_elem = item.select_one(".epl-title")
            date_elem = item.select_one(".epl-date")

            raw_num_str = num_elem.get_text(strip=True) if num_elem else ""
            title_str = title_elem.get_text(strip=True) if title_elem else a_tag.get_text(strip=True)
            date_str = date_elem.get_text(strip=True) if date_elem else None

            ep_num = cls.extract_episode_number(raw_num_str or title_str, url)

            episodes.append(
                EpisodeSummary(
                    episode_number=ep_num,
                    title=title_str,
                    url=url,
                    release_date=date_str
                )
            )

        # Sort ascending by episode_number
        episodes.sort(key=lambda ep: ep.episode_number)
        return episodes
