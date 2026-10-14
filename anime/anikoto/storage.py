"""SQLite WAL mode Storage & Persistence for Anikoto Scraper."""

import json
import sqlite3
import datetime
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from .config import DB_PATH, DATA_DIR
from .models import (
    AnikotoSeriesDetail,
    AnikotoEpisode,
    AnikotoStreamResult,
    AnikotoCrawlStats,
)

logger = logging.getLogger("anikoto.storage")


class AnikotoStorage:
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
            CREATE TABLE IF NOT EXISTS anikoto_series (
                anime_id TEXT PRIMARY KEY,
                slug TEXT UNIQUE,
                title TEXT,
                total_episodes INTEGER DEFAULT 0,
                data_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS anikoto_episodes (
                episode_id TEXT PRIMARY KEY,
                anime_id TEXT,
                episode_num INTEGER,
                title TEXT,
                server_param TEXT,
                data_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (anime_id) REFERENCES anikoto_series (anime_id)
            );

            CREATE TABLE IF NOT EXISTS anikoto_streams (
                episode_id TEXT,
                server_name TEXT,
                server_type TEXT,
                master_m3u8 TEXT,
                data_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (episode_id, server_name, server_type)
            );

            CREATE INDEX IF NOT EXISTS idx_series_slug ON anikoto_series(slug);
            CREATE INDEX IF NOT EXISTS idx_episodes_anime_id ON anikoto_episodes(anime_id);
            CREATE INDEX IF NOT EXISTS idx_streams_episode_id ON anikoto_streams(episode_id);
            """)

    def save_series(self, detail: AnikotoSeriesDetail):
        """Insert or update series and episode metadata."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO anikoto_series (anime_id, slug, title, total_episodes, data_json, updated_at)
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
                    INSERT INTO anikoto_episodes (episode_id, anime_id, episode_num, title, server_param, data_json, updated_at)
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

    def get_series(self, anime_id_or_slug: str, max_age_seconds: Optional[int] = 86400 * 7) -> Optional[AnikotoSeriesDetail]:
        """Fetch series by anime_id or slug."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json, updated_at FROM anikoto_series WHERE anime_id = ? OR slug = ?",
                (anime_id_or_slug, anime_id_or_slug),
            ).fetchone()
            if row:
                if max_age_seconds and row["updated_at"]:
                    try:
                        updated_at = datetime.datetime.fromisoformat(row["updated_at"])
                        if updated_at.tzinfo is None:
                            updated_at = updated_at.replace(tzinfo=datetime.timezone.utc)
                        age = (datetime.datetime.now(datetime.timezone.utc) - updated_at).total_seconds()
                        if age > max_age_seconds:
                            logger.info(f"Cache expired for {anime_id_or_slug} (age: {int(age)}s > {max_age_seconds}s)")
                            return None
                    except Exception:
                        pass
                return AnikotoSeriesDetail.model_validate_json(row["data_json"])
        return None

    def save_stream(self, stream: AnikotoStreamResult):
        """Save decrypted stream result."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO anikoto_streams (episode_id, server_name, server_type, master_m3u8, data_json, updated_at)
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

    def get_stream(self, episode_id: str, server_name: str, server_type: str) -> Optional[AnikotoStreamResult]:
        """Fetch cached stream result."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json FROM anikoto_streams WHERE episode_id = ? AND server_name = ? AND server_type = ?",
                (episode_id, server_name, server_type),
            ).fetchone()
            if row:
                return AnikotoStreamResult.model_validate_json(row["data_json"])
        return None

    def get_stats(self) -> AnikotoCrawlStats:
        """Get aggregate counts from database."""
        with self._get_connection() as conn:
            series_count = conn.execute("SELECT COUNT(*) FROM anikoto_series").fetchone()[0]
            episodes_count = conn.execute("SELECT COUNT(*) FROM anikoto_episodes").fetchone()[0]
            streams_count = conn.execute("SELECT COUNT(*) FROM anikoto_streams").fetchone()[0]
            last_crawled = conn.execute("SELECT MAX(updated_at) FROM anikoto_series").fetchone()[0]

            return AnikotoCrawlStats(
                total_series=series_count,
                total_episodes=episodes_count,
                total_streams=streams_count,
                last_crawled_at=last_crawled,
            )

    def export_json(self, target_path: Path):
        """Export all cached series to a JSON file."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT data_json FROM anikoto_series ORDER BY updated_at DESC").fetchall()
            series_list = [json.loads(row["data_json"]) for row in rows]
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(series_list, f, indent=2, ensure_ascii=False)
