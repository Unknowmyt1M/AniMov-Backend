# Anikoto Anime Scraper

Independent, production-grade scraper for **Anikoto** (`https://anikoto.cz/`).

## Architecture & Reverse-Engineering Highlights
- **Dynamic Catalog Extraction**:
  - Search: `/filter?keyword={query}` with multi-page parsing.
  - Detail & Episode List: Loads anime details from `/watch/{slug}` and queries `/ajax/episode/list/{anime_id}` for clean, zero-VRF episode metadata.
  - Sub & Dub Server Resolution: `/ajax/server/list?servers={server_param}` maps all available streaming mirrors.
- **MegaPlay Stream Decryption**:
  - Automatically fetches embed player source (`https://megaplay.buzz/stream/...`)
  - Queries `/stream/getSourcesNew?id={player_id}`
  - Decrypts `enc` payload using reverse-engineered AES-256-CBC cipher with custom seed keys (`MEGAPLAY_KEY_SEED` & `MEGAPLAY_IV_SEED`).
  - Extracts direct master HLS `.m3u8` playlist, multi-language subtitle tracks (.vtt), and intro/outro skip times.
- **DNS Poisoning & ISP Bypass**:
  - Uses `curl_cffi` Chrome 124 TLS impersonation with `CurlOpt.RESOLVE` and Google DoH (`https://dns.google/resolve`) to bypass local ISP censorship and connection resets.
- **SQLite WAL Mode Storage**:
  - Persistent caching in `data/anikoto.db`.

## CLI Usage

### Search Anime
```bash
python -m anime.anikoto.cli --search "Solo Leveling"
```

### Series Detail & Episodes
```bash
python -m anime.anikoto.cli --detail "solo-leveling-season-2-arise-from-the-shadow-3eukp"
```

### Stream Episode (Decrypted master m3u8 + subs)
```bash
python -m anime.anikoto.cli --episode "solo-leveling-season-2-arise-from-the-shadow-3eukp" --ep 1 --server-type sub
```

### Crawl & Pre-cache Series
```bash
python -m anime.anikoto.cli --crawl "solo-leveling-season-2-arise-from-the-shadow-3eukp" --max-episodes 3
```

### Database Stats
```bash
python -m anime.anikoto.cli --stats
```
