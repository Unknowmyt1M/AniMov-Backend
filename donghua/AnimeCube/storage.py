"""
SQLite persistence with Write-Ahead Logging (WAL) for AnimeCube scraper.
"""
import json
import sqlite3
from typing import Optional, List, Dict, Any
from pathlib import Path

from .config import DB_PATH, OUTPUT_DIR
from .models import SeriesDetail, EpisodeDetail, EpisodeSummary, StreamServer, CrawlStats


class Storage:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS series (
                slug TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                aliases TEXT,
                status TEXT,
                year INTEGER,
                total_episodes INTEGER,
                genres TEXT,
                tags TEXT,
                synopsis TEXT,
                cover_image TEXT,
                update_days TEXT,
                update_time TEXT,
                extra_meta TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS episodes (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                series_slug TEXT NOT NULL,
                episode_number REAL NOT NULL,
                title TEXT NOT NULL,
                season_id TEXT,
                duration INTEGER,
                published_at TEXT,
                prev_episode TEXT,
                next_episode TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (series_slug) REFERENCES series (slug) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_id TEXT NOT NULL,
                server_name TEXT NOT NULL,
                provider TEXT NOT NULL,
                embed_url TEXT NOT NULL,
                quality TEXT,
                languages TEXT,
                FOREIGN KEY (episode_id) REFERENCES episodes (id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_episodes_series ON episodes(series_slug);
            CREATE INDEX IF NOT EXISTS idx_servers_ep ON servers(episode_id);
            """)

    def save_series(self, series: SeriesDetail):
        with self._get_connection() as conn:
            conn.execute("""
            INSERT INTO series (
                slug, url, title, aliases, status, year, total_episodes,
                genres, tags, synopsis, cover_image, update_days, update_time,
                extra_meta, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(slug) DO UPDATE SET
                url=excluded.url,
                title=excluded.title,
                aliases=excluded.aliases,
                status=excluded.status,
                year=excluded.year,
                total_episodes=excluded.total_episodes,
                genres=excluded.genres,
                tags=excluded.tags,
                synopsis=excluded.synopsis,
                cover_image=excluded.cover_image,
                update_days=excluded.update_days,
                update_time=excluded.update_time,
                extra_meta=excluded.extra_meta,
                updated_at=CURRENT_TIMESTAMP
            """, (
                series.slug,
                series.url,
                series.title,
                json.dumps(series.aliases, ensure_ascii=False),
                series.status,
                series.year,
                series.total_episodes,
                json.dumps(series.genres, ensure_ascii=False),
                json.dumps(series.tags, ensure_ascii=False),
                series.synopsis,
                series.cover_image,
                json.dumps(series.update_days, ensure_ascii=False),
                series.update_time,
                json.dumps(series.extra_meta, ensure_ascii=False)
            ))

            for ep in series.episodes:
                conn.execute("""
                INSERT INTO episodes (id, url, series_slug, episode_number, title, season_id, duration, published_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    url=excluded.url,
                    episode_number=excluded.episode_number,
                    title=excluded.title,
                    season_id=excluded.season_id,
                    duration=excluded.duration,
                    published_at=excluded.published_at
                """, (ep.id, ep.url, series.slug, ep.episode_number, ep.title, ep.season_id, ep.duration, ep.published_at))

    def save_episode_detail(self, ep: EpisodeDetail):
        with self._get_connection() as conn:
            conn.execute("""
            INSERT INTO episodes (
                id, url, series_slug, episode_number, title, duration, published_at,
                prev_episode, next_episode, status, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                url=excluded.url,
                episode_number=excluded.episode_number,
                title=excluded.title,
                duration=excluded.duration,
                published_at=excluded.published_at,
                prev_episode=excluded.prev_episode,
                next_episode=excluded.next_episode,
                status='completed',
                updated_at=CURRENT_TIMESTAMP
            """, (ep.id, ep.url, ep.series_slug, ep.episode_number, ep.title, ep.duration, ep.published_at, ep.prev_episode, ep.next_episode))

            conn.execute("DELETE FROM servers WHERE episode_id = ?", (ep.id,))
            for s in ep.servers:
                conn.execute("""
                INSERT INTO servers (episode_id, server_name, provider, embed_url, quality, languages)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (ep.id, s.server_name, s.provider, s.embed_url, s.quality, json.dumps(s.languages)))

    def get_stats(self) -> CrawlStats:
        with self._get_connection() as conn:
            total_series = conn.execute("SELECT COUNT(*) FROM series").fetchone()[0]
            total_episodes = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
            completed = conn.execute("SELECT COUNT(*) FROM episodes WHERE status = 'completed'").fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM episodes WHERE status = 'pending'").fetchone()[0]
            failed = conn.execute("SELECT COUNT(*) FROM episodes WHERE status = 'failed'").fetchone()[0]

            return CrawlStats(
                total_series=total_series,
                total_episodes=total_episodes,
                completed_episodes=completed,
                pending_episodes=pending,
                failed_episodes=failed
            )

    def export_series_json(self, slug: str) -> Optional[Path]:
        with self._get_connection() as conn:
            s_row = conn.execute("SELECT * FROM series WHERE slug = ?", (slug,)).fetchone()
            if not s_row:
                return None

            series_data = dict(s_row)
            series_data["aliases"] = json.loads(series_data["aliases"]) if series_data["aliases"] else []
            series_data["genres"] = json.loads(series_data["genres"]) if series_data["genres"] else []
            series_data["tags"] = json.loads(series_data["tags"]) if series_data["tags"] else []
            series_data["update_days"] = json.loads(series_data["update_days"]) if series_data["update_days"] else []
            series_data["extra_meta"] = json.loads(series_data["extra_meta"]) if series_data["extra_meta"] else {}

            ep_rows = conn.execute("SELECT * FROM episodes WHERE series_slug = ? ORDER BY episode_number ASC", (slug,)).fetchall()
            episodes_data = []

            for ep in ep_rows:
                ep_dict = dict(ep)
                srv_rows = conn.execute("SELECT * FROM servers WHERE episode_id = ?", (ep["id"],)).fetchall()
                ep_dict["servers"] = [
                    {
                        "server_name": s["server_name"],
                        "provider": s["provider"],
                        "embed_url": s["embed_url"],
                        "quality": s["quality"],
                        "languages": json.loads(s["languages"]) if s["languages"] else []
                    }
                    for s in srv_rows
                ]
                episodes_data.append(ep_dict)

            series_data["episodes"] = episodes_data
            output_file = OUTPUT_DIR / f"{slug}.json"
            output_file.write_text(json.dumps(series_data, indent=2, ensure_ascii=False), encoding="utf-8")
            return output_file
