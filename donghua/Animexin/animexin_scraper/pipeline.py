"""Orchestrator: discover -> detail -> episodes -> embeds."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from .browser import fetch_with_browser
from .config import Config
from .discovery import discover_catalog, search_catalog
from .episode_parser import parse_episode_label
from .exporter import export_json
from .http_client import HtmlCache, HttpClient, RetryExhausted, fetch_cached
from .models import AnimeCard, Embed, ServerOption
from .parser import parse_detail, parse_episode_page
from .players import classify_provider, extract_embeds_from_html
from .storage import Storage

log = logging.getLogger("animexin")


class Pipeline:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.http = HttpClient(cfg)
        self.cache = HtmlCache(cfg.html_cache_dir, cfg.cache_enabled)
        self.store = Storage(cfg.db_path)

    def run(self) -> None:
        cfg = self.cfg
        if cfg.reset:
            self.store.wipe()
            log.info("Database wiped (--reset)")
        if cfg.retry_failed:
            n = self.store.reset_failed()
            log.info("Reset %d failed rows (--retry-failed)", n)
        if cfg.validate_only:
            path, res = export_json(cfg, self.store)
            log.info("Validated %s: %s", path, res["errors"] or "OK")
            return

        # --- seed anime rows ---
        if cfg.detail_url:
            existing = self.store.anime_by_url(cfg.detail_url)
            title = existing["title"] if existing and existing["title"] else cfg.detail_url
            aid = self.store.upsert_anime(AnimeCard(url=cfg.detail_url, title=title), reset_state=cfg.refresh)
            target = self.store.anime_by_id(aid)
            pending = [target] if target else []
        elif cfg.search_query:
            cards = search_catalog(self.http, self.cache, cfg.source, cfg.search_query, refresh=cfg.refresh)
            log.info("Search %r: %d results", cfg.search_query, len(cards))
            if cfg.max_anime:
                cards = cards[: cfg.max_anime]
            seeded_ids = [self.store.upsert_anime(c, reset_state=cfg.refresh) for c in cards]
            pending = [r for aid in seeded_ids if (r := self.store.anime_by_id(aid))]
        else:
            cards = discover_catalog(self.http, self.cache, cfg.source, refresh=cfg.refresh)
            log.info("Catalog: %d anime", len(cards))
            if cfg.max_anime and not cfg.full:
                cards = cards[: cfg.max_anime]
            for c in cards:
                self.store.upsert_anime(c, reset_state=cfg.refresh)
            pending = self.store.pending_anime(cfg.title_filter, include_complete=cfg.refresh)

        log.info("Processing %d anime (filter=%s)", len(pending), cfg.title_filter)
        with ThreadPoolExecutor(max_workers=max(1, cfg.concurrency)) as pool:
            futs = {pool.submit(self.process_anime, row["id"], row["url"]): row["id"] for row in pending}
            for fut in as_completed(futs):
                try:
                    fut.result()
                except Exception as exc:
                    log.exception("Anime %s failed: %s", futs[fut], exc)
        if cfg.export:
            path, res = export_json(cfg, self.store)
            log.info("Exported %s stats=%s errors=%s", path, res["stats"], res["errors"] or "none")
        self.http.close()
        self.store.close()

    def _fetch(self, url: str) -> str:
        try:
            return fetch_cached(self.http, self.cache, url, refresh=self.cfg.refresh)
        except RetryExhausted:
            if self.cfg.use_browser_fallback:
                log.info("Static fetch failed, trying browser: %s", url)
                html = fetch_with_browser(url, headless=self.cfg.headless,
                                          wait_ms=self.cfg.browser_wait_ms)
                self.cache.put(url, html)
                return html
            raise

    def process_anime(self, aid: int, url: str) -> None:
        cfg = self.cfg
        try:
            html = self._fetch(url)
        except Exception as exc:
            self.store.mark_anime_state(aid, "failed", str(exc))
            return
        detail = parse_detail(html, url)
        if not detail.title:
            self.store.mark_anime_state(aid, "failed", "empty title")
            return
        self.store.set_anime_detail(aid, detail)
        episodes = detail.episodes
        if cfg.max_episodes_per_anime is not None:
            # keep oldest N (list is newest-first in DOM)
            episodes = list(reversed(episodes))[: cfg.max_episodes_per_anime]
        for entry in episodes:
            meta = parse_episode_label(entry.raw_label, entry.title)
            try:
                eid = self.store.upsert_episode(aid, entry, meta)
            except Exception as exc:
                log.warning("Episode upsert failed %s: %s", entry.url, exc)
                continue
            self.process_episode(eid, entry.url)
        self.store.finalize_anime(aid)

    def process_episode(self, eid: int, url: str) -> None:
        cfg = self.cfg
        row = self.store.episode_by_id(eid)
        if row and row["state"] == "done" and cfg.resume and not cfg.refresh:
            return
        if cfg.refresh:
            self.store.clear_episode_embeds(eid)
        try:
            html = self._fetch(url)
        except Exception as exc:
            self.store.mark_episode(eid, "failed", str(exc))
            return
        page = parse_episode_page(html, url)
        servers = page.servers
        if cfg.max_servers_per_episode is not None:
            servers = servers[: cfg.max_servers_per_episode]
        embeds: list[Embed] = list(page.embeds)
        # fetch per-server variant pages when server URLs point at site pages
        if cfg.discover_embeds:
            for srv in servers:
                sid = self.store.upsert_server(eid, srv)
                if srv.url.startswith(cfg.source.rstrip("/")) or "animexin" in srv.url:
                    try:
                        shtml = self._fetch(srv.url)
                        for em in extract_embeds_from_html(shtml, srv.url):
                            em["server_label"] = srv.label
                            embeds.append(Embed(**em))
                        self.store.mark_server(sid, "done")
                    except Exception as exc:
                        self.store.mark_server(sid, "failed", str(exc))
                else:
                    # direct third-party embed
                    embeds.append(Embed(provider=classify_provider(srv.url), url=srv.url,
                                        origin="static", server_label=srv.label))
                    self.store.mark_server(sid, "done")
        # store embeds (dedupe by URL)
        seen: set[str] = set()
        for em in embeds:
            if em.url in seen:
                continue
            seen.add(em.url)
            self.store.add_embed(eid, None, em)
        # browser re-render when nothing found
        if not embeds and cfg.use_browser_fallback:
            try:
                bhtml = fetch_with_browser(url, headless=cfg.headless, wait_ms=cfg.browser_wait_ms)
                for em in extract_embeds_from_html(bhtml, url):
                    if em["url"] not in seen:
                        seen.add(em["url"])
                        self.store.add_embed(eid, None,
                                             Embed(provider=em["provider"], url=em["url"],
                                                   origin="browser", server_label=em.get("server_label", "")))
            except Exception as exc:
                log.debug("Browser fallback failed %s: %s", url, exc)
        stored_embeds = self.store.embeds_for_episode(eid)
        if stored_embeds:
            self.store.mark_episode(eid, "done")
        else:
            self.store.mark_episode(eid, "failed", "no embeds found")
