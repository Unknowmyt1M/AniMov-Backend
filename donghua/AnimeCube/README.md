# AnimeCube Scraper & AES-GCM Stream Resolver

High-performance crawler, metadata extractor, and client-side AES-GCM video stream decryptor specifically engineered for **AnimeCube** (`https://animecube.live/`).

## Architecture & Reverse-Engineering Breakdown

### 1. Platform Architecture
- Unlike traditional WordPress donghua sites (Animexin, Lucifer Donghua, DonghuaStream, AnimeKhor), AnimeCube is built on **Next.js App Router (React Server Components / RSC)**.
- Series metadata, schedules, tabs, and episode listings are embedded in streaming `self.__next_f.push([1, "..."])` RSC chunks inside the initial HTML document.

### 2. Client-Side Video Stream Protection (AES-GCM Decryption Protocol)
AnimeCube does **NOT** expose static server selectors in HTML. Instead, video sources are loaded asynchronously via a 2-stage encrypted REST API:

1. **Stage 1 — Version Registry (`/api/anime-sources-versions`)**:
   - The client generates a random 16-byte hex nonce: `X-Obf`.
   - Sends `GET /api/anime-sources-versions` with headers `X-Obf` and `Accept: application/json`.
   - The server responds with `X-Registry-ETag: <etag>` and encrypted base64 payload `{ "d": "..." }`.
   - **Key Derivation**: `Key = SHA-256(X-Obf + "|" + ETag)`.
   - **Ciphertext format**: First 12 bytes = IV, remaining bytes = AES-GCM ciphertext + 16-byte authentication tag.
   - **Decrypted JSON**: Contains `{ "bySeason": { [slug]: { [primaryTabId]: { [seasonId]: "<version_hash>" } } } }`.

2. **Stage 2 — Episode Video Sources (`/api/anime/{slug}/episode/{episodeId}/sources`)**:
   - Requests `/api/anime/{slug}/episode/{episodeId}/sources?v={version_hash}&primaryTabId={primaryTabId}&seasonId={seasonId}`.
   - Supplies a new random 16-byte hex nonce: `X-Obf`.
   - **Key Derivation**: `Key = SHA-256(X-Obf + "|" + version_hash)`.
   - **Ciphertext format**: First 12 bytes = IV, remaining bytes = AES-GCM ciphertext + tag.
   - **Decrypted JSON**: Provides exact streaming sources:
     - **Dailymotion**: `https://geo.dailymotion.com/player.html?video={videoId}` (with `privateId` and quality flags)
     - **Rumble**: `https://rumble.com/embed/{videoId}/`
     - **YouTube**: `https://www.youtube.com/embed/{videoId}`

### 3. Bot Detection Bypass
- AnimeCube checks for `navigator.webdriver` or empty `navigator.languages`. If detected, it redirects to Google Search or throws HTTP 451.
- Handled in Python via `curl_cffi` with Chrome 124 TLS/JA3 impersonation and realistic browser header generation.
- Stealth browser flags configured in Playwright fallback sniffer.

### 4. Modules Overview
- `decryptor.py`: Implements `AnimeCubeStreamResolver` with registry caching (ETag + TTL), AES-GCM decryption, automatic retry on version rotation, and embed URL generators.
- `rsc_parser.py`: Fast zero-browser Next.js RSC parser with balanced JSON chunk extraction.
- `scraper.py`: High-level crawler orchestrating catalog listing, series metadata parsing, stream resolution, and persistence.
- `storage.py`: SQLite WAL-mode database storing relational series, episodes, and stream servers.
- `cli.py`: Interactive Rich terminal interface with table formatting.

---

## CLI Usage

### View Full Catalog
```bash
python -m donghua.AnimeCube.cli --catalog
```

### Search Series
```bash
python -m donghua.AnimeCube.cli --search "Shrouding"
```

### Get Series Details & Episode List
```bash
python -m donghua.AnimeCube.cli --info "shrouding-the-heavens"
```

### Get Episode Playback Details & Decrypted Stream Servers
```bash
python -m donghua.AnimeCube.cli --episode "lord-of-mysteries" --ep "1"
python -m donghua.AnimeCube.cli --episode "shrouding-the-heavens" --ep "183"
```

### Crawl Series to SQLite Database
```bash
python -m donghua.AnimeCube.cli --crawl "lord-of-mysteries" --max-episodes 5
```

### View Database Stats & Export to JSON
```bash
python -m donghua.AnimeCube.cli --stats
python -m donghua.AnimeCube.cli --export "lord-of-mysteries"
```
