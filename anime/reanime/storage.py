"""SQLite WAL mode Storage & Persistence for ReAnime Scraper."""

import json
import sqlite3
import datetime
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from .config import DB_PATH, DATA_DIR
from .models import (
    ReAnimeSeriesDetail,
    ReAnimeEpisode,
    ReAnimeStreamResult,
    ReAnimeCrawlStats,
)

logger = logging.getLogger("reanime.storage")


class ReAnimeStorage:
    """Manages SQLite database with WAL mode for cached ReAnime data."""

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
            CREATE TABLE IF NOT EXISTS reanime_series (
                slug TEXT PRIMARY KEY,
                title TEXT,
                total_episodes INTEGER DEFAULT 0,
                data_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reanime_episodes (
                id TEXT PRIMARY KEY,
                slug TEXT,
                episode_num INTEGER,
                title TEXT,
                data_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (slug) REFERENCES reanime_series (slug)
            );

            CREATE TABLE IF NOT EXISTS reanime_streams (
                stream_id TEXT PRIMARY KEY,
                slug TEXT,
                episode_num INTEGER,
                embed_url TEXT,
                status TEXT,
                data_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_reanime_ep_slug ON reanime_episodes(slug);
            CREATE INDEX IF NOT EXISTS idx_reanime_stream_slug ON reanime_streams(slug, episode_num);
            """)

    def save_series(self, detail: ReAnimeSeriesDetail):
        """Insert or update series and all its episodes."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reanime_series (slug, title, total_episodes, data_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(slug) DO UPDATE SET
                    title = excluded.title,
                    total_episodes = excluded.total_episodes,
                    data_json = excluded.data_json,
                    updated_at = excluded.updated_at
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
                    INSERT INTO reanime_episodes (id, slug, episode_num, title, data_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        title = excluded.title,
                        data_json = excluded.data_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        ep.id,
                        detail.slug,
                        ep.episode_num,
                        ep.title,
                        ep.model_dump_json(),
                        now,
                    ),
                )

    def get_series(self, slug: str, max_age_seconds: Optional[int] = 86400 * 7) -> Optional[ReAnimeSeriesDetail]:
        """Fetch cached series details by slug."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json, updated_at FROM reanime_series WHERE slug = ?",
                (slug,),
            ).fetchone()
            if row:
                if max_age_seconds and row["updated_at"]:
                    try:
                        updated_at = datetime.datetime.fromisoformat(row["updated_at"])
                        if updated_at.tzinfo is None:
                            updated_at = updated_at.replace(tzinfo=datetime.timezone.utc)
                        age = (datetime.datetime.now(datetime.timezone.utc) - updated_at).total_seconds()
                        if age > max_age_seconds:
                            logger.info(f"Cache expired for {slug} (age: {int(age)}s > {max_age_seconds}s)")
                            return None
                    except Exception:
                        pass
                data = json.loads(row["data_json"])
                return ReAnimeSeriesDetail(**data)
        return None

    def save_stream(self, stream: ReAnimeStreamResult):
        """Insert or update stream result."""
        stream_id = f"{stream.slug}:{stream.episode_num}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reanime_streams (stream_id, slug, episode_num, embed_url, status, data_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(stream_id) DO UPDATE SET
                    embed_url = excluded.embed_url,
                    status = excluded.status,
                    data_json = excluded.data_json,
                    updated_at = excluded.updated_at
                """,
                (
                    stream_id,
                    stream.slug,
                    stream.episode_num,
                    stream.embed_url,
                    stream.status,
                    stream.model_dump_json(),
                    now,
                ),
            )

    def get_stream(self, slug: str, episode_num: int) -> Optional[ReAnimeStreamResult]:
        """Fetch cached stream result."""
        stream_id = f"{slug}:{episode_num}"
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json FROM reanime_streams WHERE stream_id = ?",
                (stream_id,),
            ).fetchone()
            if row:
                data = json.loads(row["data_json"])
                return ReAnimeStreamResult(**data)
        return None

    def get_stats(self) -> ReAnimeCrawlStats:
        """Calculate counts across all tables."""
        with self._get_connection() as conn:
            total_series = conn.execute("SELECT COUNT(*) FROM reanime_series").fetchone()[0]
            total_episodes = conn.execute("SELECT COUNT(*) FROM reanime_episodes").fetchone()[0]
            total_streams = conn.execute("SELECT COUNT(*) FROM reanime_streams").fetchone()[0]
            row = conn.execute("SELECT MAX(updated_at) FROM reanime_series").fetchone()
            last_crawled = row[0] if row and row[0] else None

            return ReAnimeCrawlStats(
                total_series=total_series,
                total_episodes=total_episodes,
                total_streams=total_streams,
                last_crawled_at=last_crawled,
            )
