"""SQLite WAL mode Storage & Persistence for AnimeSuge Scraper."""

import json
import sqlite3
import datetime
import logging
from pathlib import Path
from typing import Optional

from .config import DB_PATH, DATA_DIR
from .models import (
    AnimeSugeSeriesDetail,
    AnimeSugeStreamResult,
    AnimeSugeCrawlStats,
)

logger = logging.getLogger("animesuge.storage")


class AnimeSugeStorage:
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
            CREATE TABLE IF NOT EXISTS animesuge_series (
                anime_id TEXT PRIMARY KEY,
                slug TEXT UNIQUE,
                title TEXT,
                total_episodes INTEGER DEFAULT 0,
                data_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS animesuge_episodes (
                episode_id TEXT PRIMARY KEY,
                anime_id TEXT,
                episode_num INTEGER,
                title TEXT,
                server_param TEXT,
                data_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (anime_id) REFERENCES animesuge_series (anime_id)
            );

            CREATE TABLE IF NOT EXISTS animesuge_streams (
                episode_id TEXT,
                server_name TEXT,
                server_type TEXT,
                master_m3u8 TEXT,
                data_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (episode_id, server_name, server_type)
            );

            CREATE INDEX IF NOT EXISTS idx_suge_series_slug ON animesuge_series(slug);
            CREATE INDEX IF NOT EXISTS idx_suge_episodes_anime_id ON animesuge_episodes(anime_id);
            CREATE INDEX IF NOT EXISTS idx_suge_streams_episode_id ON animesuge_streams(episode_id);
            """)

    def save_series(self, detail: AnimeSugeSeriesDetail):
        """Insert or update series and episode metadata."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO animesuge_series (anime_id, slug, title, total_episodes, data_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(anime_id) DO UPDATE SET
                    slug=excluded.slug,
                    title=excluded.title,
                    total_episodes=excluded.total_episodes,
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at
                """,
                (
                    detail.anime_id,
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
                    INSERT INTO animesuge_episodes (episode_id, anime_id, episode_num, title, server_param, data_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(episode_id) DO UPDATE SET
                        anime_id=excluded.anime_id,
                        episode_num=excluded.episode_num,
                        title=excluded.title,
                        server_param=excluded.server_param,
                        data_json=excluded.data_json,
                        updated_at=excluded.updated_at
                    """,
                    (
                        ep.id,
                        detail.anime_id,
                        ep.episode_num,
                        ep.title,
                        ep.server_param,
                        ep.model_dump_json(),
                        now,
                    ),
                )

    def get_series(self, anime_id_or_slug: str, max_age_seconds: Optional[int] = None) -> Optional[AnimeSugeSeriesDetail]:
        """Fetch series by anime_id or slug with optional TTL freshness check."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json, updated_at FROM animesuge_series WHERE anime_id = ? OR slug = ?",
                (anime_id_or_slug, anime_id_or_slug),
            ).fetchone()
            if row:
                if max_age_seconds is not None and row["updated_at"]:
                    try:
                        updated_time = datetime.datetime.fromisoformat(row["updated_at"])
                        if (datetime.datetime.now(datetime.timezone.utc) - updated_time).total_seconds() > max_age_seconds:
                            return None
                    except Exception:
                        pass
                return AnimeSugeSeriesDetail.model_validate_json(row["data_json"])
        return None

    def save_stream(self, stream: AnimeSugeStreamResult):
        """Save decrypted stream result."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO animesuge_streams (episode_id, server_name, server_type, master_m3u8, data_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(episode_id, server_name, server_type) DO UPDATE SET
                    master_m3u8=excluded.master_m3u8,
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at
                """,
                (
                    stream.episode_id,
                    stream.server_name,
                    stream.server_type,
                    stream.master_m3u8,
                    stream.model_dump_json(),
                    now,
                ),
            )

    def get_stream(self, episode_id: str, server_name: str, server_type: str) -> Optional[AnimeSugeStreamResult]:
        """Fetch cached stream result."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json FROM animesuge_streams WHERE episode_id = ? AND server_name = ? AND server_type = ?",
                (episode_id, server_name, server_type),
            ).fetchone()
            if row:
                return AnimeSugeStreamResult.model_validate_json(row["data_json"])
        return None

    def get_stats(self) -> AnimeSugeCrawlStats:
        """Get aggregate counts from database."""
        with self._get_connection() as conn:
            series_count = conn.execute("SELECT COUNT(*) FROM animesuge_series").fetchone()[0]
            episodes_count = conn.execute("SELECT COUNT(*) FROM animesuge_episodes").fetchone()[0]
            streams_count = conn.execute("SELECT COUNT(*) FROM animesuge_streams").fetchone()[0]
            last_crawled = conn.execute("SELECT MAX(updated_at) FROM animesuge_series").fetchone()[0]

            return AnimeSugeCrawlStats(
                total_series=series_count,
                total_episodes=episodes_count,
                total_streams=streams_count,
                last_crawled_at=last_crawled,
            )

    def export_json(self, target_path: Path):
        """Export all cached series to a JSON file."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT data_json FROM animesuge_series ORDER BY updated_at DESC").fetchall()
            series_list = [json.loads(row["data_json"]) for row in rows]
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(series_list, f, indent=2, ensure_ascii=False)
