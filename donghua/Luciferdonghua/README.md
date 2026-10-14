# Lucifer Donghua Production Scraper 🐉⚡

High-performance reverse-engineered scraper engine for **Lucifer Donghua** (`https://luciferdonghua.in`).

Extracts complete Donghua metadata, character & voice actors roster, episode listings (with 4K and batch ranges `04 & 05`), multi-server video mirrors (Rumble, Dailymotion, VidHide, OK.ru), and direct download links.

---

## 🌟 Key Features

1. ⚡ **Sub-Second Speed via TLS Impersonation**: Uses `curl_cffi` (Chrome 124 TLS profile) to cleanly bypass Cloudflare anti-bot blocks on `luciferdonghua.in`.
2. 🔄 **On-Disk SHA1 HTML Caching**: Pages are cached locally (`cache/<sha1>.html`). Zero redundant network bandwidth on restarts or pauses.
3. 💾 **SQLite WAL Persistence**: Database (`data/lucifer.db`) in WAL mode with thread-safe `threading.RLock()` for high-concurrency scraping and complete state machines (`discovered` -> `detail_parsed` -> `complete`).
4. 🎭 **Characters & Voice Actors Roster**: Extracts character names, roles (Main / Supporting), and avatar pictures.
5. 🎬 **Server Mirror Embed Resolution**: Automatically resolves video server routes (`/v/1/`, `/v/2/`, `/v/3/`, etc.) into clean embed iframes for:
   - Dailymotion 4K
   - Rumble 4K
   - VidHide / Yurn 4K
   - OK.ru 4K
   - Direct download links (`misterdonghua.in`)
6. 🎯 **Advanced Donghua Numbering**: Handles batch episodes (`04 & 05 [4K]`), all-time counters (`158 [243]`), decimals (`6.5`), and ensures natural ascending sort (1 -> N).
7. 🛡️ **Playwright Stream Sniffer**: Headless Chromium fallback that intercepts CDP network traffic for direct `.m3u8` or `.mp4` URLs.

---

## 💻 CLI Commands

Run from the workspace root:

### 1. Search for a Donghua
```bash
python -m donghua.Luciferdonghua.cli --search "Golden Curse"
```

### 2. View Complete Metadata & Episodes
```bash
python -m donghua.Luciferdonghua.cli --info "golden-curse"
```

### 3. Parse Episode Streaming Mirrors & Downloads
```bash
python -m donghua.Luciferdonghua.cli --episode "https://luciferdonghua.in/golden-curse-episode-09-luicfer-donghua/"
```

### 4. Crawl Entire Series into Database
```bash
# Crawl series and all episodes
python -m donghua.Luciferdonghua.cli --crawl "golden-curse"

# Crawl with limit (e.g. 3 episodes)
python -m donghua.Luciferdonghua.cli --crawl "golden-curse" --max-episodes 3
```

### 5. Browse Catalog
```bash
python -m donghua.Luciferdonghua.cli --catalog --pages 2
```

### 6. View Database Stats
```bash
python -m donghua.Luciferdonghua.cli --stats
```

### 7. Export Series to JSON
```bash
python -m donghua.Luciferdonghua.cli --export "golden-curse"
```
*(Saved into `donghua/Luciferdonghua/output/golden-curse.json`)*
