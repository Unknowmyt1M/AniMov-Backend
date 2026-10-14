"""
SQLite storage backend for Miruro anime metadata, episodes, and stream sources.
Operates in WAL mode for ACID-compliant concurrent reads/writes.
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from .config import DB_PATH, OUTPUT_DIR
from .models import SeriesDetail, EpisodeDetail, EpisodeSummary, StreamMirror, SubtitleTrack, CrawlStats


class Storage:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS series (
                id TEXT PRIMARY KEY,
                title_english TEXT,
                title_romaji TEXT,
                title_native TEXT,
                format TEXT,
                status TEXT,
                season TEXT,
                season_year INTEGER,
                episode_count INTEGER,
                average_score REAL,
                popularity INTEGER,
                cover_url TEXT,
                banner_url TEXT,
                genres TEXT,
                tags TEXT,
                studios TEXT,
                description TEXT,
                external_ids TEXT,
                updated_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS episodes (
                id TEXT PRIMARY KEY,
                anime_id TEXT,
                episode_number REAL,
                title TEXT,
                thumbnail_url TEXT,
                duration_minutes INTEGER,
                aired_at TEXT,
                subtitles TEXT,
                servers TEXT,
                downloads TEXT,
                status TEXT DEFAULT 'completed',
                updated_at TIMESTAMP,
                FOREIGN KEY (anime_id) REFERENCES series (id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_episodes_anime_id ON episodes (anime_id);
            CREATE INDEX IF NOT EXISTS idx_episodes_num ON episodes (anime_id, episode_number);
            """)

    def save_series(self, series: SeriesDetail):
        with self._get_connection() as conn:
            conn.execute("""
            INSERT INTO series (
                id, title_english, title_romaji, title_native, format, status,
                season, season_year, episode_count, average_score, popularity,
                cover_url, banner_url, genres, tags, studios, description, external_ids, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title_english=excluded.title_english,
                title_romaji=excluded.title_romaji,
                title_native=excluded.title_native,
                format=excluded.format,
                status=excluded.status,
                season=excluded.season,
                season_year=excluded.season_year,
                episode_count=excluded.episode_count,
                average_score=excluded.average_score,
                popularity=excluded.popularity,
                cover_url=excluded.cover_url,
                banner_url=excluded.banner_url,
                genres=excluded.genres,
                tags=excluded.tags,
                studios=excluded.studios,
                description=excluded.description,
                external_ids=excluded.external_ids,
                updated_at=excluded.updated_at;
            """, (
                series.id,
                series.title_english,
                series.title_romaji,
                series.title_native,
                series.format,
                series.status,
                series.season,
                series.season_year,
                series.episode_count,
                series.average_score,
                series.popularity,
                series.cover_url,
                series.banner_url,
                json.dumps(series.genres, ensure_ascii=False),
                json.dumps(series.tags, ensure_ascii=False),
                json.dumps(series.studios, ensure_ascii=False),
                series.description,
                json.dumps(series.external_ids, ensure_ascii=False),
                datetime.utcnow().isoformat()
            ))

            for ep in series.episodes:
                conn.execute("""
                INSERT INTO episodes (
                    id, anime_id, episode_number, title, thumbnail_url,
                    duration_minutes, aired_at, status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    thumbnail_url=excluded.thumbnail_url,
                    duration_minutes=excluded.duration_minutes,
                    aired_at=excluded.aired_at;
                """, (
                    ep.id,
                    series.id,
                    ep.episode_number,
                    ep.title,
                    ep.thumbnail_url,
                    ep.duration_minutes,
                    ep.aired_at,
                    datetime.utcnow().isoformat()
                ))

    def save_episode_detail(self, ep: EpisodeDetail):
        with self._get_connection() as conn:
            conn.execute("""
            INSERT INTO episodes (
                id, anime_id, episode_number, title, thumbnail_url,
                subtitles, servers, downloads, status, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                thumbnail_url=excluded.thumbnail_url,
                subtitles=excluded.subtitles,
                servers=excluded.servers,
                downloads=excluded.downloads,
                status='completed',
                updated_at=excluded.updated_at;
            """, (
                ep.id,
                ep.anime_id,
                ep.episode_number,
                ep.title,
                ep.thumbnail_url,
                json.dumps([s.model_dump() for s in ep.subtitles], ensure_ascii=False),
                json.dumps([s.model_dump() for s in ep.servers], ensure_ascii=False),
                json.dumps(ep.downloads, ensure_ascii=False),
                datetime.utcnow().isoformat()
            ))

    def get_series(self, anime_id: str) -> Optional[SeriesDetail]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM series WHERE id = ?", (anime_id,)).fetchone()
            if not row:
                return None

            ep_rows = conn.execute(
                "SELECT * FROM episodes WHERE anime_id = ? ORDER BY episode_number ASC",
                (anime_id,)
            ).fetchall()

            episodes = [
                EpisodeSummary(
                    id=r["id"],
                    episode_number=r["episode_number"],
                    title=r["title"],
                    thumbnail_url=r["thumbnail_url"],
                    duration_minutes=r["duration_minutes"],
                    aired_at=r["aired_at"]
                )
                for r in ep_rows
            ]

            return SeriesDetail(
                id=row["id"],
                title_english=row["title_english"],
                title_romaji=row["title_romaji"],
                title_native=row["title_native"],
                format=row["format"],
                status=row["status"],
                season=row["season"],
                season_year=row["season_year"],
                episode_count=row["episode_count"],
                average_score=row["average_score"],
                popularity=row["popularity"],
                cover_url=row["cover_url"],
                banner_url=row["banner_url"],
                genres=json.loads(row["genres"] or "[]"),
                tags=json.loads(row["tags"] or "[]"),
                studios=json.loads(row["studios"] or "[]"),
                description=row["description"],
                external_ids=json.loads(row["external_ids"] or "{}"),
                episodes=episodes
            )

    def get_stats(self) -> CrawlStats:
        with self._get_connection() as conn:
            total_series = conn.execute("SELECT COUNT(*) FROM series").fetchone()[0]
            total_episodes = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
            completed_episodes = conn.execute("SELECT COUNT(*) FROM episodes WHERE status = 'completed'").fetchone()[0]
            pending_episodes = conn.execute("SELECT COUNT(*) FROM episodes WHERE status = 'pending'").fetchone()[0]
            failed_episodes = conn.execute("SELECT COUNT(*) FROM episodes WHERE status = 'failed'").fetchone()[0]

            return CrawlStats(
                total_series=total_series,
                total_episodes=total_episodes,
                completed_episodes=completed_episodes,
                pending_episodes=pending_episodes,
                failed_episodes=failed_episodes
            )

    def export_series_json(self, anime_id: str) -> Optional[Path]:
        series = self.get_series(anime_id)
        if not series:
            return None

        out_path = OUTPUT_DIR / f"{anime_id}.json"
        with self._get_connection() as conn:
            ep_rows = conn.execute(
                "SELECT * FROM episodes WHERE anime_id = ? ORDER BY episode_number ASC",
                (anime_id,)
            ).fetchall()

            episodes_data = []
            for r in ep_rows:
                episodes_data.append({
                    "id": r["id"],
                    "episode_number": r["episode_number"],
                    "title": r["title"],
                    "thumbnail_url": r["thumbnail_url"],
                    "duration_minutes": r["duration_minutes"],
                    "subtitles": json.loads(r["subtitles"] or "[]"),
                    "servers": json.loads(r["servers"] or "[]"),
                    "downloads": json.loads(r["downloads"] or "[]"),
                    "status": r["status"]
                })

        data = series.model_dump()
        data["episodes"] = episodes_data

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return out_path
