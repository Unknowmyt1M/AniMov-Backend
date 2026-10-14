"""
SQLite persistence with Write-Ahead Logging (WAL) for AnimeKhor scraper.
"""
import json
import sqlite3
from typing import Optional, List, Dict, Any
from pathlib import Path

from .config import DB_PATH, OUTPUT_DIR
from .models import SeriesDetail, EpisodeDetail, EpisodeSummary, StreamServer, DownloadOption, CrawlStats


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
                native_title TEXT,
                rating TEXT,
                status TEXT,
                studio TEXT,
                country TEXT,
                released_date TEXT,
                duration TEXT,
                season TEXT,
                type_name TEXT,
                genres TEXT,
                synopsis TEXT,
                poster TEXT,
                extra_meta TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS episodes (
                url TEXT PRIMARY KEY,
                series_slug TEXT NOT NULL,
                episode_number REAL NOT NULL,
                title TEXT NOT NULL,
                release_date TEXT,
                prev_episode TEXT,
                next_episode TEXT,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (series_slug) REFERENCES series (slug) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_url TEXT NOT NULL,
                server_name TEXT NOT NULL,
                provider TEXT NOT NULL,
                embed_url TEXT NOT NULL,
                quality TEXT,
                languages TEXT,
                FOREIGN KEY (episode_url) REFERENCES episodes (url) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_url TEXT NOT NULL,
                title TEXT NOT NULL,
                host TEXT,
                url TEXT NOT NULL,
                quality TEXT,
                FOREIGN KEY (episode_url) REFERENCES episodes (url) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_episodes_series ON episodes(series_slug);
            CREATE INDEX IF NOT EXISTS idx_servers_ep ON servers(episode_url);
            CREATE INDEX IF NOT EXISTS idx_downloads_ep ON downloads(episode_url);
            """)

    def save_series(self, series: SeriesDetail):
        with self._get_connection() as conn:
            conn.execute("""
            INSERT INTO series (
                slug, url, title, native_title, rating, status, studio, country,
                released_date, duration, season, type_name, genres, synopsis,
                poster, extra_meta, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(slug) DO UPDATE SET
                url=excluded.url,
                title=excluded.title,
                native_title=excluded.native_title,
                rating=excluded.rating,
                status=excluded.status,
                studio=excluded.studio,
                country=excluded.country,
                released_date=excluded.released_date,
                duration=excluded.duration,
                season=excluded.season,
                type_name=excluded.type_name,
                genres=excluded.genres,
                synopsis=excluded.synopsis,
                poster=excluded.poster,
                extra_meta=excluded.extra_meta,
                updated_at=CURRENT_TIMESTAMP
            """, (
                series.slug,
                series.url,
                series.title,
                series.native_title,
                series.rating,
                series.status,
                series.studio,
                series.country,
                series.released_date,
                series.duration,
                series.season,
                series.type_name,
                json.dumps(series.genres, ensure_ascii=False),
                series.synopsis,
                series.poster,
                json.dumps(series.extra_meta, ensure_ascii=False)
            ))

            for ep in series.episodes:
                conn.execute("""
                INSERT INTO episodes (url, series_slug, episode_number, title, release_date)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    episode_number=excluded.episode_number,
                    title=excluded.title,
                    release_date=excluded.release_date
                """, (ep.url, series.slug, ep.episode_number, ep.title, ep.release_date))

    def save_episode_detail(self, ep: EpisodeDetail, series_slug: Optional[str] = None):
        with self._get_connection() as conn:
            slug = series_slug
            if not slug:
                cur = conn.execute("SELECT series_slug FROM episodes WHERE url = ?", (ep.url,))
                row = cur.fetchone()
                if row and row["series_slug"]:
                    slug = row["series_slug"]
                elif ep.series_url:
                    slug_match = re.search(r'/anime/([^/]+)/?', ep.series_url)
                    slug = slug_match.group(1) if slug_match else ep.series_url.strip("/").split("/")[-1]
                else:
                    slug = "unknown"

            # Auto-ensure series exists in series table to satisfy FK constraint
            series_title = ep.series_title or (slug.replace("-", " ").title() if slug != "unknown" else "Unknown Series")
            series_url = ep.series_url or f"https://animekhor.org/anime/{slug}/"
            conn.execute("""
            INSERT INTO series (slug, url, title)
            VALUES (?, ?, ?)
            ON CONFLICT(slug) DO NOTHING
            """, (slug, series_url, series_title))

            conn.execute("""
            INSERT INTO episodes (
                url, series_slug, episode_number, title, release_date,
                prev_episode, next_episode, status, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'completed', CURRENT_TIMESTAMP)
            ON CONFLICT(url) DO UPDATE SET
                series_slug=excluded.series_slug,
                episode_number=excluded.episode_number,
                title=excluded.title,
                release_date=excluded.release_date,
                prev_episode=excluded.prev_episode,
                next_episode=excluded.next_episode,
                status='completed',
                updated_at=CURRENT_TIMESTAMP
            """, (ep.url, slug, ep.episode_number, ep.title, ep.release_date, ep.prev_episode, ep.next_episode))

            conn.execute("DELETE FROM servers WHERE episode_url = ?", (ep.url,))
            for s in ep.servers:
                conn.execute("""
                INSERT INTO servers (episode_url, server_name, provider, embed_url, quality, languages)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (ep.url, s.server_name, s.provider, s.embed_url, s.quality, json.dumps(s.languages)))

            conn.execute("DELETE FROM downloads WHERE episode_url = ?", (ep.url,))
            for d in ep.downloads:
                conn.execute("""
                INSERT INTO downloads (episode_url, title, host, url, quality)
                VALUES (?, ?, ?, ?, ?)
                """, (ep.url, d.title, d.host, d.url, d.quality))

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
            series_data["genres"] = json.loads(series_data["genres"]) if series_data["genres"] else []
            series_data["extra_meta"] = json.loads(series_data["extra_meta"]) if series_data["extra_meta"] else {}

            ep_rows = conn.execute("SELECT * FROM episodes WHERE series_slug = ? ORDER BY episode_number ASC", (slug,)).fetchall()
            episodes_data = []

            for ep in ep_rows:
                ep_dict = dict(ep)
                srv_rows = conn.execute("SELECT * FROM servers WHERE episode_url = ?", (ep["url"],)).fetchall()
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

                dl_rows = conn.execute("SELECT * FROM downloads WHERE episode_url = ?", (ep["url"],)).fetchall()
                ep_dict["downloads"] = [
                    {"title": d["title"], "host": d["host"], "url": d["url"], "quality": d["quality"]}
                    for d in dl_rows
                ]
                episodes_data.append(ep_dict)

            series_data["episodes"] = episodes_data
            output_file = OUTPUT_DIR / f"{slug}.json"
            output_file.write_text(json.dumps(series_data, indent=2, ensure_ascii=False), encoding="utf-8")
            return output_file
