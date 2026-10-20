"""Streaming Proxy with Automatic HLS Playlist URL Rewriting."""

import logging
import re
from urllib.parse import urljoin, quote, unquote
from typing import Optional
from fastapi import Response, HTTPException
from fastapi.responses import StreamingResponse
import httpx

logger = logging.getLogger("animov.proxy")

def rewrite_m3u8_playlist(content: str, base_url: str, referer: Optional[str] = None) -> str:
    """Rewrite all variant and segment URLs in an m3u8 playlist to route via proxy."""
    ref_param = f"&referer={quote(referer)}" if referer else ""
    lines = content.splitlines()
    rewritten = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("#"):
            # Check for URI="..." tags in metadata lines
            def replace_uri(match):
                inner_uri = match.group(1)
                full_uri = urljoin(base_url, inner_uri)
                proxied = f"/api/stream/proxy?url={quote(full_uri)}{ref_param}"
                return f'URI="{proxied}"'

            new_line = re.sub(r'URI="([^"]+)"', replace_uri, stripped)
            rewritten.append(new_line)
        else:
            # Segment or child m3u8 URL line
            full_segment_url = urljoin(base_url, stripped)
            proxied_segment = f"/api/stream/proxy?url={quote(full_segment_url)}{ref_param}"
            rewritten.append(proxied_segment)

    return "\n".join(rewritten)


async def handle_stream_proxy(url: str, referer: Optional[str] = None):
    """Fetch and proxy stream chunks and m3u8 playlists without CORS or referer errors."""
    clean_url = unquote(url)
    default_referer = referer or "https://megaplay.buzz/"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Referer": default_referer,
        "Origin": default_referer.rstrip("/"),
    }

    client = httpx.AsyncClient(headers=headers, timeout=20.0, follow_redirects=True)

    try:
        req = client.build_request("GET", clean_url)
        resp = await client.send(req, stream=True)

        if resp.status_code >= 400:
            await resp.aclose()
            await client.aclose()
            raise HTTPException(status_code=resp.status_code, detail=f"Upstream stream error {resp.status_code}")

        content_type = resp.headers.get("content-type", "")
        is_playlist = (
            "mpegurl" in content_type or
            clean_url.endswith(".m3u8") or
            "m3u8" in clean_url
        )

        if is_playlist:
            # Read full text to inspect content
            content_bytes = await resp.aread()
            await resp.aclose()
            await client.aclose()

            text = content_bytes.decode("utf-8", errors="replace")

            # Check if this is a WebVTT / SRT subtitle file rather than an HLS playlist
            if text.startswith("WEBVTT") or "WEBVTT" in text[:60]:
                return Response(
                    content=text,
                    media_type="text/vtt; charset=utf-8",
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "GET, OPTIONS",
                        "Access-Control-Allow-Headers": "*",
                        "Cache-Control": "public, max-age=86400",
                    },
                )

            rewritten = rewrite_m3u8_playlist(text, clean_url, default_referer)

            return Response(
                content=rewritten,
                media_type="application/vnd.apple.mpegurl",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Cache-Control": "no-cache",
                },
            )
        else:
            # Binary segment chunk (.ts, .aac, mp4)
            async def chunk_generator():
                try:
                    async for chunk in resp.aiter_bytes():
                        yield chunk
                finally:
                    await resp.aclose()
                    await client.aclose()

            return StreamingResponse(
                chunk_generator(),
                media_type=content_type or "video/mp2t",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Cache-Control": "public, max-age=3600",
                },
            )

    except HTTPException:
        raise
    except Exception as e:
        await client.aclose()
        logger.error(f"Stream proxy failure for {clean_url}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
