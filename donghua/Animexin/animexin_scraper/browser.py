"""Optional Playwright fallback: re-render JS-gated pages and return HTML."""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def fetch_with_browser(url: str, *, headless: bool = True, wait_ms: int = 5000) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("playwright is not installed (pip install playwright)") from exc
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"))
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(wait_ms)
            return page.content()
        finally:
            ctx.close()
            browser.close()
