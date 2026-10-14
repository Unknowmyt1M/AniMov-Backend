"""
Playwright CDP network response sniffer for AnimeKhor to intercept direct m3u8 and mp4 video streams.
"""
import re
from typing import Optional, List, Dict, Any


class StreamSniffer:
    VIDEO_EXTENSIONS = ('.m3u8', '.mp4', '.mpd', '/master.m3u8', '/index.m3u8')
    BLACKLIST_PATTERNS = ('googlesyndication', 'doubleclick', 'analytics', 'clarity.ms', 'adnxs')

    @classmethod
    def is_target_stream(cls, url: str) -> bool:
        low = url.lower()
        if any(b in low for b in cls.BLACKLIST_PATTERNS):
            return False
        return any(ext in low for ext in cls.VIDEO_EXTENSIONS) or 'playlist' in low

    @classmethod
    def sniff(cls, embed_url: str, timeout_seconds: int = 15) -> Dict[str, Any]:
        result = {
            "embed_url": embed_url,
            "stream_url": None,
            "type": None,
            "all_captured": []
        }

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            result["error"] = "Playwright is not installed"
            return result

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )

                captured = []

                def handle_response(response):
                    req_url = response.url
                    if cls.is_target_stream(req_url):
                        captured.append(req_url)

                page.on("response", handle_response)

                try:
                    page.goto(embed_url, timeout=timeout_seconds * 1000, wait_until="commit")
                    page.wait_for_timeout(4000)
                except Exception:
                    pass
                finally:
                    browser.close()

                if captured:
                    result["stream_url"] = captured[0]
                    result["all_captured"] = list(dict.fromkeys(captured))
                    result["type"] = "m3u8" if ".m3u8" in captured[0].lower() else "mp4"

        except Exception as e:
            result["error"] = str(e)

        return result
