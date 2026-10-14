"""SQLite WAL mode Storage & Persistence for WatchAnimeWorld Scraper."""

import json
import sqlite3
import datetime
import logging
from pathlib import Path
from typing import Optional

from .config import DB_PATH, DATA_DIR
from .models import (
    WatchAnimeWorldSeriesDetail,
    WatchAnimeWorldEpisode,
    WatchAnimeWorldCrawlStats,
)

logger = logging.getLogger("watchanimeworld.storage")


class WatchAnimeWorldStorage:
    """Manages SQLite database with WAL mode for cached anime data."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create tables and indexes."""
        with self._get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS waw_series (
                slug TEXT PRIMARY KEY,
                title TEXT,
                total_episodes INTEGER DEFAULT 0,
                data_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS waw_episodes (
                slug TEXT PRIMARY KEY,
                series_slug TEXT,
                episode_num INTEGER,
                season_num INTEGER,
                title TEXT,
                data_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (series_slug) REFERENCES waw_series (slug)
            );

            CREATE INDEX IF NOT EXISTS idx_waw_episodes_series ON waw_episodes(series_slug);
            """)

    def save_series(self, detail: WatchAnimeWorldSeriesDetail):
        """Insert or update series and episode metadata."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO waw_series (slug, title, total_episodes, data_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(slug) DO UPDATE SET
                    title=excluded.title,
                    total_episodes=excluded.total_episodes,
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at
                """,
                (
                    detail.slug,
                    detail.title,
                    detail.total_episodes,
                    detail.model_dump_json(),
                    now,
                ),
            )

            for ep in detail.episodes:
                conn.execute(
                    """
                    INSERT INTO waw_episodes (slug, series_slug, episode_num, season_num, title, data_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(slug) DO UPDATE SET
                        series_slug=excluded.series_slug,
                        episode_num=excluded.episode_num,
                        season_num=excluded.season_num,
                        title=excluded.title,
                        data_json=excluded.data_json,
                        updated_at=excluded.updated_at
                    """,
                    (
                        ep.slug,
                        detail.slug,
                        ep.episode_num,
                        ep.season_num,
                        ep.title,
                        ep.model_dump_json(),
                        now,
                    ),
                )

    def get_series(self, slug: str, max_age_seconds: Optional[int] = None) -> Optional[WatchAnimeWorldSeriesDetail]:
        """Fetch series by slug with optional TTL check."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json, updated_at FROM waw_series WHERE slug = ?",
                (slug,),
            ).fetchone()
            if row:
                if max_age_seconds is not None and row["updated_at"]:
                    try:
                        updated_time = datetime.datetime.fromisoformat(row["updated_at"])
                        if (datetime.datetime.now(datetime.timezone.utc) - updated_time).total_seconds() > max_age_seconds:
                            return None
                    except Exception:
                        pass
                return WatchAnimeWorldSeriesDetail.model_validate_json(row["data_json"])
        return None

    def save_episode(self, series_slug: str, ep: WatchAnimeWorldEpisode):
        """Save episode with servers."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO waw_episodes (slug, series_slug, episode_num, season_num, title, data_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(slug) DO UPDATE SET
                    series_slug=excluded.series_slug,
                    episode_num=excluded.episode_num,
                    season_num=excluded.season_num,
                    title=excluded.title,
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at
                """,
                (
                    ep.slug,
                    series_slug,
                    ep.episode_num,
                    ep.season_num,
                    ep.title,
                    ep.model_dump_json(),
                    now,
                ),
            )

    def get_episode(self, ep_slug: str) -> Optional[WatchAnimeWorldEpisode]:
        """Fetch episode by slug."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json FROM waw_episodes WHERE slug = ?",
                (ep_slug,),
            ).fetchone()
            if row:
                return WatchAnimeWorldEpisode.model_validate_json(row["data_json"])
        return None

    def get_stats(self) -> WatchAnimeWorldCrawlStats:
        """Get aggregate counts from database."""
        with self._get_connection() as conn:
            series_count = conn.execute("SELECT COUNT(*) FROM waw_series").fetchone()[0]
            episodes_count = conn.execute("SELECT COUNT(*) FROM waw_episodes").fetchone()[0]
            streams_count = conn.execute("SELECT COUNT(*) FROM waw_episodes WHERE data_json LIKE '%servers%'").fetchone()[0]
            last_crawled = conn.execute("SELECT MAX(updated_at) FROM waw_series").fetchone()[0]

            return WatchAnimeWorldCrawlStats(
                total_series=series_count,
                total_episodes=episodes_count,
                total_streams=streams_count,
                last_crawled_at=last_crawled,
            )

    def export_json(self, target_path: Path):
        """Export all cached series to a JSON file."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT data_json FROM waw_series ORDER BY updated_at DESC").fetchall()
            series_list = [json.loads(row["data_json"]) for row in rows]
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(series_list, f, indent=2, ensure_ascii=False)
