"""SQLite persistence with resume support.

anime    : discovered -> detail_parsed -> complete | partial | failed
episodes : pending -> done | failed
servers  : pending -> done | failed
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

from .episode_parser import EpisodeMeta
from .models import AnimeCard, DetailPage, Embed, EpisodeEntry, ServerOption
from .utils import normalize_url

_SCHEMA = """
CREATE TABLE IF NOT EXISTS anime (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    title TEXT, poster_url TEXT, synopsis TEXT, genres TEXT,
    rating TEXT, quality TEXT, audio TEXT,
    status TEXT, anime_type TEXT,
    site_episode_count INTEGER,
    discovered_episode_count INTEGER NOT NULL DEFAULT 0,
    successful_episode_count INTEGER NOT NULL DEFAULT 0,
    failed_episode_count INTEGER NOT NULL DEFAULT 0,
    state TEXT NOT NULL DEFAULT 'discovered',
    last_error TEXT, retries INTEGER NOT NULL DEFAULT 0,
    created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anime_id INTEGER NOT NULL,
    url TEXT UNIQUE NOT NULL,
    episode_number INTEGER, part INTEGER, episode_type TEXT, episode_title TEXT,
    raw_label TEXT, range_start INTEGER, range_end INTEGER,
    release_date TEXT, subtitle_lang TEXT, dom_order INTEGER,
    state TEXT NOT NULL DEFAULT 'pending',
    last_error TEXT, retries INTEGER NOT NULL DEFAULT 0,
    created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER NOT NULL,
    label TEXT, url TEXT NOT NULL, idx INTEGER,
    state TEXT NOT NULL DEFAULT 'pending',
    last_error TEXT, retries INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS embeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER NOT NULL,
    server_id INTEGER, server_label TEXT, provider TEXT,
    url TEXT NOT NULL, dedup_key TEXT NOT NULL DEFAULT '',
    origin TEXT NOT NULL DEFAULT 'static', created_at TEXT,
    UNIQUE (episode_id, dedup_key)
);
CREATE INDEX IF NOT EXISTS idx_episodes_anime ON episodes(anime_id);
CREATE INDEX IF NOT EXISTS idx_servers_episode ON servers(episode_id);
CREATE INDEX IF NOT EXISTS idx_embeds_episode ON embeds(episode_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_servers_unique ON servers(episode_id, url);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Storage:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except sqlite3.ProgrammingError:
                pass

    def upsert_anime(self, card: AnimeCard, reset_state: bool = False) -> int:
        now = utcnow()
        with self._lock:
            state_clause = ", state='discovered'" if reset_state else ""
            cur = self._conn.execute(
                f"""INSERT INTO anime (url, title, poster_url, status, anime_type,
                                      state, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'discovered', ?, ?)
                   ON CONFLICT(url) DO UPDATE SET title=excluded.title,
                     poster_url=excluded.poster_url, status=excluded.status,
                     anime_type=excluded.anime_type{state_clause}, updated_at=excluded.updated_at
                   RETURNING id""",
                (normalize_url(card.url), card.title, card.poster_url,
                 card.status, card.card_type, now, now))
            row = cur.fetchone()
            self._conn.commit()
            return int(row["id"])

    def anime_by_url(self, url: str) -> Optional[sqlite3.Row]:
        with self._lock:
            return self._conn.execute("SELECT * FROM anime WHERE url = ?",
                                      (normalize_url(url),)).fetchone()

    def anime_by_id(self, aid: int) -> Optional[sqlite3.Row]:
        with self._lock:
            return self._conn.execute("SELECT * FROM anime WHERE id = ?", (aid,)).fetchone()

    def pending_anime(self, slug: Optional[str] = None, include_complete: bool = False) -> list[sqlite3.Row]:
        states = "('discovered','detail_parsed','partial','failed','complete')" if include_complete else "('discovered','detail_parsed','partial','failed')"
        q = f"SELECT * FROM anime WHERE state IN {states}"
        args: tuple = ()
        if slug:
            q += " AND url LIKE ? COLLATE NOCASE"
            args = (f"%{slug}%",)
        q += " ORDER BY id"
        with self._lock:
            return list(self._conn.execute(q, args).fetchall())

    def all_anime(self) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._conn.execute("SELECT * FROM anime ORDER BY id").fetchall())

    def set_anime_detail(self, aid: int, detail: DetailPage) -> None:
        with self._lock:
            self._conn.execute(
                """UPDATE anime SET title=?, poster_url=?, synopsis=?, genres=?,
                   rating=?, quality=?, audio=?, status=?, anime_type=?,
                   site_episode_count=?, state='detail_parsed', updated_at=?
                   WHERE id=?""",
                (detail.title, detail.poster_url, detail.synopsis,
                 json.dumps(detail.genres), detail.rating, json.dumps(detail.quality),
                 json.dumps(detail.audio), detail.status, detail.anime_type,
                 detail.site_episode_count, utcnow(), aid))
            self._conn.commit()

    def mark_anime_state(self, aid: int, state: str, error: str = "") -> None:
        with self._lock:
            self._conn.execute("UPDATE anime SET state=?, last_error=?, updated_at=? WHERE id=?",
                               (state, error or None, utcnow(), aid))
            self._conn.commit()

    def episode_counts(self, anime_id: int) -> dict:
        with self._lock:
            row = self._conn.execute(
                """SELECT COUNT(*) AS d,
                   COALESCE(SUM(CASE WHEN state='done' THEN 1 ELSE 0 END),0) AS s,
                   COALESCE(SUM(CASE WHEN state='failed' THEN 1 ELSE 0 END),0) AS f
                   FROM episodes WHERE anime_id=?""", (anime_id,)).fetchone()
        d, s, f = int(row["d"] or 0), int(row["s"] or 0), int(row["f"] or 0)
        return {"discovered": d, "successful": s, "failed": f, "pending": d - s - f}

    def finalize_anime(self, aid: int, error: str = "") -> None:
        c = self.episode_counts(aid)
        with self._lock:
            self._conn.execute(
                """UPDATE anime SET discovered_episode_count=?, successful_episode_count=?,
                   failed_episode_count=?, updated_at=? WHERE id=?""",
                (c["discovered"], c["successful"], c["failed"], utcnow(), aid))
            self._conn.commit()
        if c["failed"] > 0:
            state = "failed" if c["successful"] == 0 else "partial"
        elif c["pending"] > 0:
            state = "partial"
        else:
            state = "complete"
        self.mark_anime_state(aid, state, error)

    def reset_failed(self) -> int:
        n = 0
        now = utcnow()
        with self._lock:
            for r in self._conn.execute("SELECT id FROM anime WHERE state='failed'").fetchall():
                self._conn.execute("UPDATE anime SET state='discovered', last_error=NULL, updated_at=? WHERE id=?", (now, r["id"]))
                n += 1
            ep_anime: set = set()
            for r in self._conn.execute("SELECT id, anime_id FROM episodes WHERE state='failed'").fetchall():
                self._conn.execute("UPDATE episodes SET state='pending', last_error=NULL, updated_at=? WHERE id=?", (now, r["id"]))
                ep_anime.add(r["anime_id"])
                n += 1
            for r in self._conn.execute("SELECT id FROM servers WHERE state='failed'").fetchall():
                self._conn.execute("UPDATE servers SET state='pending', last_error=NULL WHERE id=?", (r["id"],))
                n += 1
            for aid in ep_anime:
                self._conn.execute("UPDATE anime SET state='detail_parsed', updated_at=? WHERE id=?", (now, aid))
            self._conn.commit()
        return n

    def upsert_episode(self, anime_id: int, entry: EpisodeEntry, meta: EpisodeMeta) -> int:
        now = utcnow()
        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO episodes (anime_id, url, episode_number, part, episode_type,
                    episode_title, raw_label, range_start, range_end, release_date,
                    subtitle_lang, dom_order, state, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                   ON CONFLICT(url) DO UPDATE SET anime_id=excluded.anime_id,
                     episode_number=excluded.episode_number, part=excluded.part,
                     episode_type=excluded.episode_type, episode_title=excluded.episode_title,
                     raw_label=excluded.raw_label, range_start=excluded.range_start,
                     range_end=excluded.range_end, release_date=excluded.release_date,
                     subtitle_lang=excluded.subtitle_lang, dom_order=excluded.dom_order,
                     updated_at=excluded.updated_at
                   RETURNING id""",
                (anime_id, normalize_url(entry.url), meta.episode_number, meta.part,
                 meta.episode_type, meta.episode_title, meta.raw_label,
                 meta.range_start, meta.range_end, entry.release_date,
                 entry.subtitle_lang, entry.dom_order, now, now))
            row = cur.fetchone()
            self._conn.commit()
            return int(row["id"])

    def episodes_for_anime(self, anime_id: int, state: Optional[str] = None) -> list[sqlite3.Row]:
        q = "SELECT * FROM episodes WHERE anime_id=?"
        args: tuple = (anime_id,)
        if state:
            q += " AND state=?"
            args = (anime_id, state)
        q += " ORDER BY dom_order, id"
        with self._lock:
            return list(self._conn.execute(q, args).fetchall())

    def episode_by_id(self, eid: int) -> Optional[sqlite3.Row]:
        with self._lock:
            return self._conn.execute("SELECT * FROM episodes WHERE id=?", (eid,)).fetchone()

    def mark_episode(self, eid: int, state: str, error: str = "") -> None:
        with self._lock:
            self._conn.execute("UPDATE episodes SET state=?, last_error=?, updated_at=? WHERE id=?",
                               (state, error or None, utcnow(), eid))
            self._conn.commit()

    def upsert_server(self, episode_id: int, opt: ServerOption) -> int:
        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO servers (episode_id, label, url, idx, state)
                   VALUES (?, ?, ?, ?, 'pending')
                   ON CONFLICT(episode_id, url) DO UPDATE SET label=excluded.label, idx=excluded.idx
                   RETURNING id""",
                (episode_id, opt.label, normalize_url(opt.url), opt.index))
            row = cur.fetchone()
            self._conn.commit()
            return int(row["id"])

    def servers_for_episode(self, episode_id: int) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._conn.execute(
                "SELECT * FROM servers WHERE episode_id=? ORDER BY idx", (episode_id,)).fetchall())

    def mark_server(self, sid: int, state: str, error: str = "") -> None:
        with self._lock:
            self._conn.execute("UPDATE servers SET state=?, last_error=? WHERE id=?",
                               (state, error or None, sid))
            self._conn.commit()

    def clear_episode_embeds(self, episode_id: int) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM embeds WHERE episode_id=?", (episode_id,))
            self._conn.commit()

    def add_embed(self, episode_id: int, server_id: Optional[int], embed: Embed) -> None:
        url = (embed.url or "").strip()
        if not url:
            return
        with self._lock:
            try:
                self._conn.execute(
                    """INSERT INTO embeds (episode_id, server_id, server_label, provider,
                                          url, dedup_key, origin, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(episode_id, dedup_key) DO UPDATE SET
                         server_id=COALESCE(excluded.server_id, embeds.server_id),
                         server_label=COALESCE(excluded.server_label, embeds.server_label),
                         provider=excluded.provider,
                         url=excluded.url,
                         origin=excluded.origin""",
                    (episode_id, server_id, embed.server_label, embed.provider,
                     url, normalize_url(url), embed.origin, utcnow()))
                self._conn.commit()
            except sqlite3.IntegrityError:
                self._conn.rollback()

    def embeds_for_episode(self, episode_id: int) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._conn.execute(
                "SELECT * FROM embeds WHERE episode_id=? ORDER BY id", (episode_id,)).fetchall())

    def stats(self) -> dict:
        with self._lock:
            return {t: self._conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                    for t in ("anime", "episodes", "servers", "embeds")}

    def wipe(self) -> None:
        with self._lock:
            for t in ("embeds", "servers", "episodes", "anime"):
                self._conn.execute(f"DELETE FROM {t}")
            self._conn.commit()
