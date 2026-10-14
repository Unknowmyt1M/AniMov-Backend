"""
SQLite WAL Persistence for Lucifer Donghua.
Provides crash-resilient storage, thread-safe upserts, and recovery.
"""

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from .config import DATABASE_PATH
from .models import LuciferDonghuaDetail, LuciferEpisodeDetail


class LuciferStorage:
    """Thread-safe SQLite storage for Lucifer Donghua scraper."""

    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA synchronous=NORMAL;")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS donghua (
                slug TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                alternative_titles TEXT,
                status TEXT,
                rating TEXT,
                total_episodes_expected TEXT,
                data_json TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'discovered',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                episode_url TEXT PRIMARY KEY,
                series_slug TEXT NOT NULL,
                episode_number REAL NOT NULL,
                title TEXT NOT NULL,
                release_date TEXT,
                data_json TEXT,
                state TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (series_slug) REFERENCES donghua (slug)
            );
            """)

            cur.execute("CREATE INDEX IF NOT EXISTS idx_lucifer_episodes_series ON episodes (series_slug);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_lucifer_episodes_state ON episodes (state);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_lucifer_donghua_state ON donghua (state);")
            self._conn.commit()

    def save_donghua(self, item: LuciferDonghuaDetail, state: str = "detail_parsed") -> None:
        now = datetime.utcnow().isoformat()
        serialized = json.dumps(item.model_dump(), ensure_ascii=False)

        with self._lock:
            cur = self._conn.cursor()
            cur.execute("""
            INSERT INTO donghua (slug, title, alternative_titles, status, rating, total_episodes_expected, data_json, state, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                title=excluded.title,
                alternative_titles=excluded.alternative_titles,
                status=excluded.status,
                rating=excluded.rating,
                total_episodes_expected=excluded.total_episodes_expected,
                data_json=excluded.data_json,
                state=excluded.state,
                updated_at=excluded.updated_at;
            """, (
                item.slug,
                item.title,
                item.alternative_titles,
                item.status,
                item.rating,
                item.total_episodes_expected,
                serialized,
                state,
                now,
                now
            ))

            for ep in item.episodes:
                cur.execute("""
                INSERT INTO episodes (episode_url, series_slug, episode_number, title, release_date, state, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                ON CONFLICT(episode_url) DO UPDATE SET
                    title=excluded.title,
                    release_date=COALESCE(excluded.release_date, episodes.release_date),
                    updated_at=excluded.updated_at;
                """, (
                    ep.url,
                    item.slug,
                    ep.episode_number,
                    ep.title,
                    ep.release_date,
                    now,
                    now
                ))

            self._conn.commit()

    def save_episode_detail(self, ep: LuciferEpisodeDetail, series_slug: str, state: str = "done") -> None:
        now = datetime.utcnow().isoformat()
        serialized = json.dumps(ep.model_dump(), ensure_ascii=False)

        with self._lock:
            cur = self._conn.cursor()
            cur.execute("""
            INSERT INTO episodes (episode_url, series_slug, episode_number, title, release_date, data_json, state, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(episode_url) DO UPDATE SET
                title=excluded.title,
                release_date=COALESCE(excluded.release_date, episodes.release_date),
                data_json=excluded.data_json,
                state=excluded.state,
                updated_at=excluded.updated_at;
            """, (
                ep.source_url,
                series_slug,
                ep.episode_number,
                ep.episode_title,
                ep.release_date,
                serialized,
                state,
                now,
                now
            ))

            cur.execute("""
            SELECT COUNT(*) as pending_count FROM episodes
            WHERE series_slug = ? AND state != 'done';
            """, (series_slug,))
            row = cur.fetchone()
            if row and row["pending_count"] == 0:
                cur.execute("UPDATE donghua SET state = 'complete', updated_at = ? WHERE slug = ?;", (now, series_slug))
            else:
                cur.execute("UPDATE donghua SET state = 'partial', updated_at = ? WHERE slug = ?;", (now, series_slug))

            self._conn.commit()

    def mark_episode_failed(self, episode_url: str) -> None:
        now = datetime.utcnow().isoformat()
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("UPDATE episodes SET state = 'failed', updated_at = ? WHERE episode_url = ?;", (now, episode_url))
            self._conn.commit()

    def get_donghua(self, slug: str) -> Optional[LuciferDonghuaDetail]:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT data_json FROM donghua WHERE slug = ?;", (slug,))
            row = cur.fetchone()
            if row and row["data_json"]:
                return LuciferDonghuaDetail.model_validate_json(row["data_json"])
            return None

    def get_pending_episodes(self, series_slug: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self._conn.cursor()
            if series_slug:
                cur.execute("""
                SELECT episode_url, series_slug, episode_number, title FROM episodes
                WHERE series_slug = ? AND state = 'pending'
                ORDER BY episode_number ASC;
                """, (series_slug,))
            else:
                cur.execute("""
                SELECT episode_url, series_slug, episode_number, title FROM episodes
                WHERE state = 'pending'
                ORDER BY series_slug, episode_number ASC;
                """)
            return [dict(r) for r in cur.fetchall()]

    def reset_failed(self) -> int:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("UPDATE episodes SET state = 'pending' WHERE state = 'failed';")
            count = cur.rowcount
            self._conn.commit()
            return count

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT COUNT(*) FROM donghua;")
            total_series = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM episodes;")
            total_episodes = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM episodes WHERE state = 'done';")
            done_episodes = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM episodes WHERE state = 'pending';")
            pending_episodes = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM episodes WHERE state = 'failed';")
            failed_episodes = cur.fetchone()[0]

            return {
                "total_series": total_series,
                "total_episodes": total_episodes,
                "completed_episodes": done_episodes,
                "pending_episodes": pending_episodes,
                "failed_episodes": failed_episodes,
            }
