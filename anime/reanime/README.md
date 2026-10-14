# ReAnime Scraper (`anime/reanime/`)

Independent, production-grade anime scraper for **ReAnime** (`https://reanime.to/`).

---

## 🌟 Architecture & Features

- **SvelteKit SSR Engine Parsing**: ReAnime is built with SvelteKit SSR. All anime metadata (AniList ID, MAL ID, English/Romaji/Native titles, seasonal tags, episode roster with Sub/Dub/Filler/Recap badges) is extracted directly from the server-rendered DOM and SvelteKit state.
- **DNS Poisoning & ISP Bypass**: Direct Cloudflare Anycast IP resolution via `curl_cffi` to prevent local ISP dropouts.
- **SQLite WAL Storage**: Thread-safe persistent cache with Write-Ahead Logging for series metadata, episode rosters, and streaming statuses.
- **Graceful Upstream Handling**: Handles upstream video provider downtimes seamlessly, categorizing streams as available or pending.
- **Rich CLI & JSON Output**: Supports interactive terminal formatting and machine-readable JSON.

---

## 🚀 CLI Usage

### Search Anime
```bash
python -m anime.reanime.cli --search "Solo Leveling"
```

### Full Series Details & Episode Roster
```bash
python -m anime.reanime.cli --detail "solo-leveling-season-2-arise-from-the-shadow-mu5hvx"
```

### Episode Stream / Server Extraction
```bash
python -m anime.reanime.cli --episode "solo-leveling-season-2-arise-from-the-shadow-mu5hvx" --ep 1
```

### Database Stats
```bash
python -m anime.reanime.cli --stats
```

### Output JSON
```bash
python -m anime.reanime.cli --search "One Piece" --json
```
