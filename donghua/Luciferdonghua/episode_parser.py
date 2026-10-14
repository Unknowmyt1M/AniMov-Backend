"""
Episode Number & Title Resolver for Lucifer Donghua.
Handles:
- Batch episodes e.g. '04 & 05 [4K]'
- Bracket numbers e.g. '158 [243]'
- Quality tags e.g. '[4K]', '[1080p]'
- Natural ascending sort
"""

import re
from typing import Tuple, Optional


RE_BATCH = re.compile(r"(\d+)\s*(?:&|and|-|to)\s*(\d+)", re.IGNORECASE)
RE_BRACKET = re.compile(r"(\d+)\s*\[(\d+)\]")
RE_EP_NUM = re.compile(r"(?:ep(?:isode)?\.?\s*|#\s*)?(\d+(?:\.\d+)?)", re.IGNORECASE)
RE_CLEAN_TAGS = re.compile(r"\[(?:4K|1080p|720p|HD|Sub|Dub)\]", re.IGNORECASE)


def parse_lucifer_episode_number(raw_text: str, fallback_index: Optional[int] = None) -> float:
    """
    Parses a float episode number from Lucifer Donghua's formatting:
    - '09 [4K]' -> 9.0
    - '04 & 05 [4K]' -> 4.0
    - '158 [243]' -> 158.0
    - 'Ep 21.5' -> 21.5
    """
    if not raw_text:
        return float(fallback_index) if fallback_index is not None else 1.0

    text = RE_CLEAN_TAGS.sub("", raw_text).strip()

    # 1. Bracket format (e.g. 158 [243])
    bracket_match = RE_BRACKET.search(text)
    if bracket_match:
        try:
            return float(bracket_match.group(1))
        except ValueError:
            pass

    # 2. Batch episode range (e.g. 04 & 05)
    batch_match = RE_BATCH.search(text)
    if batch_match:
        try:
            return float(batch_match.group(1))
        except ValueError:
            pass

    # 3. Standard numeric pattern
    num_match = RE_EP_NUM.search(text)
    if num_match:
        try:
            return float(num_match.group(1))
        except ValueError:
            pass

    if fallback_index is not None:
        return float(fallback_index)

    return 1.0


def resolve_episode_title_and_number(
    raw_num: str,
    raw_title: str,
    index: int = 1
) -> Tuple[float, str, str]:
    """
    Returns (episode_number, clean_title, quality_tag: '4K'|'1080p').
    """
    quality = "4K" if "4K" in raw_num or "4K" in raw_title else "1080p"
    ep_num = parse_lucifer_episode_number(raw_num, fallback_index=None)

    cleaned_title = raw_title.strip()
    if cleaned_title.lower() in ("ep", "episode", "sub", ""):
        cleaned_title = f"Episode {int(ep_num) if ep_num.is_integer() else ep_num}"

    return ep_num, cleaned_title, quality
