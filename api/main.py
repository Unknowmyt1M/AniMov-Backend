"""AniMov Backend FastAPI Engine for AniTube."""

import logging
from typing import Optional, List, Dict, Any
from urllib.parse import quote
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from anime.anikage.scraper import AnikageScraper
from api.resolver import StreamResolver
from api.proxy import handle_stream_proxy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("animov.api")

app = FastAPI(
    title="AniMov Backend API",
    description="Unified Anime & Media Scraper REST Engine for AniTube",
    version="1.0.0",
)

# Enable CORS for local Vite development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared scraper instance
scraper = AnikageScraper()


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "AniMov Backend API", "version": "1.0.0"}


@app.get("/api/anime/home")
def get_home_feed():
    """Fetch real-time homepage data: trending anime series and latest releasing anime."""
    try:
        trending = scraper.get_catalog(sort="trending", page=1, limit=12)
        latest_airing = scraper.get_catalog(sort="updated", page=1, limit=16)

        return {
            "trending": [r.model_dump() for r in trending],
            "latestAiring": [r.model_dump() for r in latest_airing],
        }
    except Exception as e:
        logger.error(f"Home feed fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/anime/search")
def search_anime(
    q: str = Query(..., min_length=1, description="Anime search keyword"),
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=50),
):
    """Search anime catalog by keyword."""
    try:
        results = scraper.search(query=q, page=page, limit=limit)
        return {"data": [r.model_dump() for r in results], "query": q, "page": page}
    except Exception as e:
        logger.error(f"Search failed for '{q}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/anime/trending")
def get_trending(
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=50),
    sort: str = Query("trending", description="Sort option: trending, popularity, updated"),
):
    """Browse catalog by trending, popularity, or recent updates."""
    try:
        results = scraper.get_catalog(sort=sort, page=page, limit=limit)
        return {"data": [r.model_dump() for r in results], "page": page, "sort": sort}
    except Exception as e:
        logger.error(f"Trending fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/anime/detail/{slug}")
def get_anime_detail(slug: str):
    """Fetch complete anime series information and episode list."""
    try:
        detail = scraper.get_detail(slug=slug, include_episodes=True)
        return {"data": detail.model_dump()}
    except Exception as e:
        logger.error(f"Failed to fetch anime detail for '{slug}': {e}")
        raise HTTPException(status_code=404, detail="Anime series not found or upstream error")


@app.get("/api/anime/episodes/{slug}")
def get_anime_episodes(slug: str):
    """Fetch episode list for a specific anime series."""
    try:
        episodes = scraper.get_episodes(slug=slug)
        return {"data": [ep.model_dump() for ep in episodes], "slug": slug, "count": len(episodes)}
    except Exception as e:
        logger.error(f"Failed to fetch episodes for '{slug}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/anime/stream/{slug}/{episode_number}")
async def get_stream_sources(
    slug: str,
    episode_number: int,
    lang: str = Query("sub", pattern="^(sub|dub)$"),
    wait_for_all: bool = Query(False),
):
    """Fetch and decrypt live playable HLS master.m3u8 stream URLs on-demand."""
    try:
        result = await StreamResolver.resolve_episode_streams(slug, episode_number, lang, wait_for_all=wait_for_all)

        # Enhance each source with a proxied URL for seamless browser playback
        proxied_sources = []
        for s in result.get("sources", []):
            raw_url = s.get("url")
            referer = s.get("referer") or ("https://anikage.cc/" if "bakayaro" in raw_url else "https://megaplay.buzz/")
            proxy_url = f"/api/stream/proxy?url={quote(raw_url)}&referer={quote(referer)}"
            proxied_sources.append({
                **s,
                "proxyUrl": proxy_url,
                "directUrl": raw_url,
            })

        # Enhance each subtitle track with a proxied URL
        proxied_subtitles = []
        for sub in result.get("subtitles", []):
            raw_sub_url = sub.get("file", "")
            referer = "https://anikage.cc/" if "bakayaro" in raw_sub_url else "https://megaplay.buzz/"
            proxy_url = f"/api/stream/proxy?url={quote(raw_sub_url)}&referer={quote(referer)}"
            proxied_subtitles.append({
                **sub,
                "proxyUrl": proxy_url,
                "directUrl": raw_sub_url,
            })

        return {
            "slug": slug,
            "episode": episode_number,
            "lang": lang,
            "count": len(proxied_sources),
            "hasMore": result.get("hasMore", False),
            "intro": result.get("intro"),
            "outro": result.get("outro"),
            "sources": proxied_sources,
            "subtitles": proxied_subtitles,
            "thumbnails": result.get("thumbnails"),
        }
    except Exception as e:
        logger.error(f"Stream resolution failed for {slug} ep {episode_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stream/proxy")
async def proxy_stream(
    url: str = Query(..., description="Target stream or chunk URL"),
    referer: Optional[str] = Query(None, description="Spoofed Referer header"),
):
    """Streaming proxy endpoint to bypass CORS and Referer restrictions for HLS streams."""
    return await handle_stream_proxy(url=url, referer=referer)
