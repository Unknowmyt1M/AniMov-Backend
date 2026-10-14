"""
Playwright Stream Sniffer for Lucifer Donghua.
Intercepts network requests via CDP to capture live .m3u8 and .mp4 URLs from player embeds.
"""

import asyncio
from typing import List, Optional, Tuple

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


class LuciferStreamSniffer:
    """Headless browser stream sniffer for Lucifer Donghua embeds."""

    def __init__(self, headless: bool = True, timeout_ms: int = 15000):
        self.headless = headless
        self.timeout_ms = timeout_ms

    async def sniff_embed(self, embed_url: str) -> List[Tuple[str, str]]:
        if not HAS_PLAYWRIGHT or not embed_url:
            return []

        captured_streams: List[Tuple[str, str]] = []
        seen = set()

        def handle_response(response):
            url = response.url.lower()
            content_type = response.headers.get("content-type", "").lower()

            is_hls = ".m3u8" in url or "application/x-mpegurl" in content_type or "vnd.apple.mpegurl" in content_type
            is_mp4 = ".mp4" in url or "video/mp4" in content_type

            if (is_hls or is_mp4) and response.url not in seen:
                # Filter out ads or tracking segments
                if not any(ad in url for ad in ["doubleclick", "analytics", "tracking", "pixel"]):
                    seen.add(response.url)
                    captured_streams.append((response.url, "hls" if is_hls else "mp4"))

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--mute-audio"]
                )
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 720}
                )
                page = await context.new_page()
                page.on("response", handle_response)

                try:
                    await page.goto(embed_url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                    try:
                        await page.click("video, button.play, .play-button, .jw-display-icon-container", timeout=2000)
                    except Exception:
                        pass

                    await page.wait_for_timeout(3000)
                except Exception:
                    pass
                finally:
                    await browser.close()

        except Exception:
            pass

        return captured_streams

    def sniff_embed_sync(self, embed_url: str) -> List[Tuple[str, str]]:
        try:
            return asyncio.run(self.sniff_embed(embed_url))
        except Exception:
            return []
