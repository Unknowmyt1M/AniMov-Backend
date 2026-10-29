#!/usr/bin/env python3
"""CLI entry point for the AnimeXin scraper.

Examples:
    python scraper.py --search "Martial Master" --max-anime 3
    python scraper.py --url "https://animexin.dev/anime/<slug>/" --max-episodes 2
    python scraper.py --max-anime 5 --max-episodes 2     # smoke test
    python scraper.py --all                              # full catalog scrape
    python scraper.py --all --refresh                    # ignore HTML cache
    python scraper.py --reset --all                      # wipe DB and scrape fresh
    python scraper.py --retry-failed --max-anime 10
    python scraper.py --validate-only
"""
from __future__ import annotations

import argparse
import logging
import sys

try:
    from .animexin_scraper.config import Config
    from .animexin_scraper.pipeline import Pipeline
except ImportError:
    try:
        from donghua.Animexin.animexin_scraper.config import Config
        from donghua.Animexin.animexin_scraper.pipeline import Pipeline
    except ImportError:
        from animexin_scraper.config import Config
        from animexin_scraper.pipeline import Pipeline


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="scraper.py", description="Scraper for https://animexin.dev/")
    p.add_argument("--search", default=None, dest="search_query", help="search query instead of catalog walk")
    p.add_argument("--url", default=None, dest="detail_url", help="scrape a single anime detail URL")
    p.add_argument("--all", action="store_true", default=None, help="full scrape (no limits)")
    p.add_argument("--refresh", action="store_true", default=None, help="ignore HTML cache and re-fetch")
    p.add_argument("--reset", action="store_true", default=None, help="wipe the SQLite database before running")
    p.add_argument("--retry-failed", action="store_true", default=None, help="reset failed rows so they are re-scraped")
    p.add_argument("--validate-only", action="store_true", default=None, help="validate the latest JSON output and exit")
    p.add_argument("--max-anime", type=int, default=None, help="limit number of anime processed")
    p.add_argument("--title-filter", default=None, dest="title_filter", help="only anime whose URL contains this slug text")
    p.add_argument("--max-episodes", type=int, default=None, dest="max_episodes_per_anime", help="limit episodes per anime")
    p.add_argument("--max-servers", type=int, default=None, dest="max_servers_per_episode", help="limit server variants per episode")
    p.add_argument("--config", default=None, help="path to config.json")
    p.add_argument("--db", default=None, dest="db_path", help="SQLite database path")
    p.add_argument("--output-dir", default=None, dest="output_dir", help="JSON output directory")
    p.add_argument("--cache", default=None, dest="cache_enabled", type=lambda x: x.lower() in ("1", "true", "yes"), help="enable/disable HTML cache")
    p.add_argument("--no-export", action="store_false", dest="export", default=None, help="skip JSON export")
    p.add_argument("--concurrency", type=int, default=None, help="worker threads")
    p.add_argument("--delay", type=float, default=None, dest="request_delay", help="delay between requests per worker")
    p.add_argument("--timeout", type=float, default=None, help="request timeout seconds")
    p.add_argument("--retries", type=int, default=None, help="retry count")
    p.add_argument("--no-browser", action="store_false", dest="use_browser_fallback", default=None, help="disable Playwright fallback")
    p.add_argument("--headful", action="store_false", dest="headless", default=None, help="run browser headed")
    p.add_argument("--log-level", default=None, choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    p.add_argument("--log-file", default=None)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    cfg = Config.load(args.config)
    overrides = {k: v for k, v in vars(args).items() if v is not None and k != "config"}
    cfg.merge(overrides)
    if args.all:
        cfg.max_anime = None
        cfg.max_episodes_per_anime = None
        cfg.full = True
    cfg.resolve_paths()

    log_kwargs = {"level": getattr(logging, cfg.log_level.upper(), logging.INFO),
                  "format": "%(asctime)s %(levelname)-7s %(name)s: %(message)s"}
    if cfg.log_file:
        log_kwargs["filename"] = cfg.log_file
    else:
        log_kwargs["stream"] = sys.stderr
    logging.basicConfig(**log_kwargs)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    log = logging.getLogger("animexin")
    log.info("Config: %s", cfg.to_dict())
    try:
        Pipeline(cfg).run()
    except KeyboardInterrupt:
        log.info("Interrupted. Re-run with --all --refresh to resume.")
        return 130
    except Exception as exc:  # noqa: BLE001
        log.exception("Fatal: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
