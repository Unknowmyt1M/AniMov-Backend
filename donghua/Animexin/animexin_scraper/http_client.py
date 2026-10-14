"""HTTP client with retries, backoff, multi-domain fallback and HTML cache."""
from __future__ import annotations

import logging
import random
import threading
import time

import httpx

from .config import Config
from .utils import sha1

log = logging.getLogger(__name__)


class RetryExhausted(Exception):
    pass


class HttpClient:
    def __init__(self, config: Config):
        self.config = config
        self._local = threading.local()
        self.active_base = config.source

    def _session(self) -> httpx.Client:
        s = getattr(self._local, "client", None)
        if s is None:
            s = httpx.Client(
                headers={
                    "User-Agent": self.config.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": self.config.source,
                },
                timeout=httpx.Timeout(self.config.timeout),
                follow_redirects=True,
            )
            self._local.client = s
        return s

    def close(self) -> None:
        s = getattr(self._local, "client", None)
        if s is not None:
            try:
                s.close()
            except Exception:
                pass
            self._local.client = None

    def _candidate_urls(self, url: str) -> list[str]:
        """If url belongs to a known mirror, try all mirrors in order."""
        out = [url]
        for mirror in getattr(self.config, "mirror_domains", []):
            m = mirror.rstrip("/") + "/"
            if url.startswith(m) and m != out[0][: len(m)]:
                pass
        # Build variants by swapping the base domain
        for mirror in getattr(self.config, "mirror_domains", []):
            base = mirror.rstrip("/") + "/"
            if url.startswith(self.config.source):
                variant = base + url[len(self.config.source):]
                if variant not in out:
                    out.append(variant)
        return out

    def get(self, url: str, *, retries: int | None = None) -> str:
        cfg = self.config
        attempts = cfg.retries if retries is None else retries
        last_exc: Exception | None = None
        for candidate in self._candidate_urls(url):
            for attempt in range(attempts + 1):
                if attempt > 0 and cfg.request_delay:
                    time.sleep(cfg.request_delay)
                try:
                    resp = self._session().get(candidate)
                    if resp.status_code == 200:
                        resp.encoding = resp.encoding or "utf-8"
                        self.active_base = candidate.rsplit("/", 1)[0] + "/"
                        return resp.text
                    if resp.status_code in (429, 500, 502, 503, 504):
                        raise httpx.HTTPStatusError(
                            f"HTTP {resp.status_code} for {candidate}",
                            request=resp.request, response=resp,
                        )
                    raise RetryExhausted(f"HTTP {resp.status_code} for {candidate}")
                except RetryExhausted:
                    break  # try next mirror domain
                except Exception as exc:
                    last_exc = exc
                    if attempt < attempts:
                        wait = min(cfg.max_backoff, cfg.backoff_base ** attempt + random.uniform(0, 0.5))
                        log.debug("Request failed %s (attempt %d/%d): %s; retry %.1fs",
                                  candidate, attempt + 1, attempts + 1, exc, wait)
                        time.sleep(wait)
        raise RetryExhausted(f"Failed to fetch {url} after {attempts + 1} attempts: {last_exc}")


class HtmlCache:
    def __init__(self, cache_dir: str, enabled: bool = True):
        self.cache_dir = cache_dir
        self.enabled = enabled

    def _path(self, url: str) -> str:
        return f"{self.cache_dir}/{sha1(url)}.html"

    def get(self, url: str) -> str | None:
        if not self.enabled:
            return None
        try:
            with open(self._path(url), "r", encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            return None

    def put(self, url: str, html: str) -> None:
        if not self.enabled:
            return
        try:
            from pathlib import Path
            Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
            with open(self._path(url), "w", encoding="utf-8") as fh:
                fh.write(html)
        except OSError:
            pass


def fetch_cached(http: HttpClient, cache: HtmlCache, url: str, *, refresh: bool = False) -> str:
    if not refresh:
        cached = cache.get(url)
        if cached is not None:
            return cached
    html = http.get(url)
    cache.put(url, html)
    return html
