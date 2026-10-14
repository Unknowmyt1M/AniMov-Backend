"""SQLite storage with WAL mode for Hindilinks4u Scraper."""

import os
import json
import sqlite3
import time
from typing import Optional, Dict, Any, List

from .config import config


class Hindilinks4uStorage:
    """Thread-safe SQLite storage for caching searches and details."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    query TEXT PRIMARY KEY,
                    results TEXT,
                    created_at REAL
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS movie_cache (
                    movie_id TEXT PRIMARY KEY,
                    slug TEXT,
                    detail TEXT,
                    created_at REAL
                );
            """)

    def get_search(self, query: str) -> Optional[List[Dict[str, Any]]]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT results, created_at FROM search_cache WHERE query = ?", (query.lower(),))
            row = cur.fetchone()
            if row:
                if (time.time() - row["created_at"]) < (config.cache_ttl_hours * 3600):
                    return json.loads(row["results"])
        return None

    def set_search(self, query: str, results: List[Dict[str, Any]]):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO search_cache (query, results, created_at) VALUES (?, ?, ?)",
                (query.lower(), json.dumps(results), time.time()),
            )

    def get_movie(self, movie_id_or_slug: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT detail, created_at FROM movie_cache WHERE movie_id = ? OR slug = ?",
                (movie_id_or_slug, movie_id_or_slug),
            )
            row = cur.fetchone()
            if row:
                if (time.time() - row["created_at"]) < (config.cache_ttl_hours * 3600):
                    return json.loads(row["detail"])
        return None

    def set_movie(self, movie_id: str, slug: str, detail: Dict[str, Any]):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO movie_cache (movie_id, slug, detail, created_at) VALUES (?, ?, ?, ?)",
                (movie_id, slug, json.dumps(detail), time.time()),
            )

    def get_stats(self) -> Dict[str, int]:
        with self._get_connection() as conn:
            searches = conn.execute("SELECT count(*) FROM search_cache").fetchone()[0]
            movies = conn.execute("SELECT count(*) FROM movie_cache").fetchone()[0]
            return {"cached_searches": searches, "cached_movies": movies}
