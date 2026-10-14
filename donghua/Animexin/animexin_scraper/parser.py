"""HTML parsing for AnimeXin (AnimeStream WordPress theme).

Verified live on https://animexin.dev/ :
  search results : article.bs / .listupd .bs / .animposx
  catalog card   : article.bs > a.tip[href], img src/data-src, .typez, .epx
  pagination     : div.hpage a.r (relative ?page=N)
  detail title   : h1.entry-title
  poster         : img.wp-post-image / div.bigcover img / og:image
  synopsis       : div.entry-content
  genres         : div.genxps a
  info           : div.info-content span (Rating/Quality/Language) + div.infox div.spe span
  episodes       : div.eplister li  (+ ul.clstyle fallback)
  servers        : select.mirror option[value] (base64)
  player         : #pembed iframe / meta embedUrl / video tags
"""
from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup

from .models import AnimeCard, DetailPage, EpisodeEntry, EpisodePage, ListingPage, ServerOption
from .players import decode_mirror_value, extract_embeds_from_soup, is_placeholder
from .utils import abs_url, dedupe_title, make_soup, normalize_text

LISTING_CARDS = "article.bs, .listupd .bs, .animposx, .result-item"
LISTING_NEXT = "div.hpage a.r"


def _card_title(art, a) -> str:
    h2 = art.select_one("h2[itemprop=headline], .tt h2, h2, h3, .tt")
    if h2:
        t = normalize_text(h2.get_text(" ", strip=True))
        if t:
            return dedupe_title(t)
    return dedupe_title(a.get("title") or a.get_text(" ", strip=True))


def parse_listing(html: str, base_url: str) -> ListingPage:
    soup = make_soup(html)
    cards: list[AnimeCard] = []
    seen: set[str] = set()
    for art in soup.select(LISTING_CARDS):
        a = art.select_one("a.tip[href]") or art.select_one("a[href]")
        if a is None:
            continue
        url = abs_url(base_url, a.get("href", ""))
        if not url or url in seen:
            continue
        # filter non-series links
        if any(x in url for x in ["-episode-", "/episode/", "/manga/", "/category/",
                                  "/tag/", "/author/", "?s=", "#"]):
            continue
        seen.add(url)
        img = art.select_one("img")
        poster = ""
        if img:
            poster = (img.get("src") or img.get("data-src")
                      or img.get("data-lazy-src") or "").strip()
            if poster.startswith("//"):
                poster = "https:" + poster
        typez = art.select_one(".limit .typez, .typez")
        card_type = normalize_text(typez.get_text(strip=True)) if typez else ""
        bt = art.select_one(".limit .bt .epx, .epx, .status")
        status = normalize_text(bt.get_text(strip=True)) if bt else ""
        cards.append(AnimeCard(url=url, title=_card_title(art, a),
                               poster_url=poster, card_type=card_type, status=status))
    nxt = soup.select_one(LISTING_NEXT)
    next_url = abs_url(base_url, nxt.get("href", "")) if nxt else None
    if next_url == base_url:
        next_url = None
    return ListingPage(cards=cards, next_url=next_url)


parse_search = parse_listing


def _parse_infox(soup: BeautifulSoup) -> dict:
    info: dict = {}
    infox = soup.select_one("div.infox")
    if infox:
        for span in infox.select("div.spe span"):
            b = span.find("b")
            if not b:
                continue
            key = normalize_text(b.get_text(" ", strip=True)).rstrip(":").strip().lower()
            rest = normalize_text(span.get_text(" ", strip=True)[len(b.get_text(" ", strip=True)):]).lstrip(":").strip()
            if not key:
                continue
            if key == "episodes":
                m = re.search(r"(\d+)", rest)
                info["episodes_count"] = int(m.group(1)) if m else None
            info[key] = rest

    # Real rating selector: div.rating strong or meta[itemprop=ratingValue]
    meta_rating = soup.find("meta", attrs={"itemprop": "ratingValue"})
    if meta_rating and meta_rating.get("content"):
        info["rating"] = meta_rating.get("content").strip()
    else:
        r_strong = soup.select_one("div.rating strong, .rating strong, .rating")
        if r_strong:
            r_text = normalize_text(r_strong.get_text(" ", strip=True))
            r_match = re.search(r"(\d+(?:\.\d+)?)", r_text)
            if r_match:
                info["rating"] = r_match.group(1)

    # AnimeXin EN block: div.info-content span "Rating: ...", "Quality: ...", "Language: ..."
    info_div = soup.select_one("div.info-content")
    if info_div:
        for span in info_div.find_all("span"):
            text = normalize_text(span.get_text(" ", strip=True))
            if "Rating" in text and "rating" not in info:
                info["rating"] = text.split(":")[-1].strip()
            elif "Quality" in text:
                info["quality"] = [x.strip() for x in text.split(":")[-1].split(",") if x.strip()]
            elif "Language" in text or "Audio" in text:
                info["audio"] = [x.strip() for x in text.split(":")[-1].split(",") if x.strip()]
    return info


def parse_detail(html: str, url: str) -> DetailPage:
    soup = make_soup(html)
    h1 = soup.select_one("div.infox h1.entry-title, h1.entry-title") or soup.find("h1")
    title = dedupe_title(h1.get_text(" ", strip=True)) if h1 else ""

    poster = ""
    img = soup.select_one("div.bigcover img") or soup.select_one("img.wp-post-image") or soup.select_one(".thumb img")
    if img:
        poster = ((img.get("src") or "").strip())
        if not poster or poster.startswith("data:") or "placeholder" in poster.lower():
            poster = (img.get("data-src") or img.get("data-lazy-src") or "").strip()
        if poster.startswith("//"):
            poster = "https:" + poster
    if not poster:
        og = soup.find("meta", attrs={"property": "og:image"})
        if og:
            poster = (og.get("content") or "").strip()

    synopsis = ""
    desc = soup.select_one("div.entry-content")
    if desc:
        # first meaningful paragraph(s)
        ps = [normalize_text(p.get_text(" ", strip=True)) for p in desc.find_all("p")]
        ps = [p for p in ps if len(p) > 20]
        synopsis = " ".join(ps[:3]) if ps else normalize_text(desc.get_text(" ", strip=True))[:2000]

    genres: list[str] = []
    genx = soup.select_one("div.genxed, div.genxps, div.genres, div.gens")
    if genx:
        genres = [normalize_text(g.get_text(strip=True)) for g in genx.find_all("a")]
        genres = [g for g in genres if g]

    info = _parse_infox(soup)

    episodes: list[EpisodeEntry] = []
    container = soup.select_one("div.eplister") or soup.select_one("ul.clstyle") or soup.select_one("#chapterlist")
    items = container.select("li") if container else []
    for i, li in enumerate(items):
        a = li.select_one("a[href]")
        if a is None:
            continue
        ep_url = abs_url(url, a.get("href", ""))
        if not ep_url:
            continue
        num_el = li.select_one(".epl-num, .epid")
        raw_label = normalize_text(num_el.get_text(" ", strip=True)) if num_el else ""
        title_el = li.select_one(".epl-title")
        if title_el:
            ep_title = normalize_text(title_el.get_text(" ", strip=True))
            if raw_label and ep_title.startswith(raw_label):
                ep_title = ep_title[len(raw_label):].strip()
        else:
            ep_title = normalize_text(a.get_text(" ", strip=True))
        date_el = li.select_one(".epl-date")
        date = normalize_text(date_el.get_text(" ", strip=True)) if date_el else ""
        sub_el = li.select_one(".epl-sub")
        sub = normalize_text(sub_el.get_text(" ", strip=True)) if sub_el else ""
        episodes.append(EpisodeEntry(url=ep_url, raw_label=raw_label or ep_title,
                                     title=ep_title or raw_label or f"Episode {i+1}",
                                     release_date=date, subtitle_lang=sub,
                                     dom_order=i, data_index=str(li.get("data-index", ""))))
    return DetailPage(url=url, title=title, poster_url=poster, synopsis=synopsis,
                      genres=genres, rating=info.get("rating", ""),
                      quality=info.get("quality", []), audio=info.get("audio", []),
                      status=info.get("status", ""), anime_type=info.get("type", ""),
                      site_episode_count=info.get("episodes_count"), episodes=episodes)


def parse_episode_page(html: str, url: str) -> EpisodePage:
    from .models import Embed
    soup = make_soup(html)
    h1 = soup.find("h1")
    title = normalize_text(h1.get_text(" ", strip=True)) if h1 else ""

    servers: list[ServerOption] = []
    for i, opt in enumerate(soup.select("select.mirror option, select[class*=mirror] option, select[class*=server] option, select[class*=player] option")):
        value = (opt.get("value") or "").strip()
        if not value:
            continue
        from .utils import normalize_text as nt
        label = nt(opt.get_text(" ", strip=True))
        decoded = decode_mirror_value(value)
        target = decoded or (value if value.startswith("http") else "")
        if not target:
            continue
        srv_url = abs_url(url, target)
        if not srv_url or is_placeholder(srv_url):
            continue
        servers.append(ServerOption(label=label, url=srv_url, index=i))

    raw_embeds = extract_embeds_from_soup(soup, url)
    embeds = [Embed(**e) if isinstance(e, dict) else e for e in raw_embeds]
    return EpisodePage(url=url, title=title, servers=servers, embeds=embeds)
