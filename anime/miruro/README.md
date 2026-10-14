# Miruro Anime Scraper & Stream Decryptor

High-performance scraper, catalog crawler, and stream decryptor specifically engineered for **Miruro** (`https://www.miruro.cx/`, landing `https://www.miruro.com/`).

---

## Technical Architecture & Reverse-Engineering Breakdown

### 1. Platform & API Overview
- Unlike traditional WordPress anime sites, Miruro is a high-speed Single Page Application (SPA) powered by Vite, React, and an optimized backend REST API.
- All requests communicate with the official Miruro API at `https://www.miruro.cx/api/v1`.

### 2. XOR + Gzip Binary Response Decryption Protocol
- Miruro obfuscates sensitive catalog metadata, search responses, and episode playback payloads by transmitting them as `application/octet-stream`.
- **Decryption Protocol**:
  1. Key: `b"miruro/catalog"` (14 bytes).
  2. Byte-wise XOR: Each byte in the payload is XORed with `key[index % len(key)]`.
  3. Gzip Decompression: The XOR-decrypted byte stream is standard Gzip compressed.
  4. UTF-8 JSON: Decompression yields clean, structured JSON data.

### 3. Multi-Provider Stream Aggregation
Miruro aggregates streams from multiple tier-1 anime providers:
- **AnimePahe**: Direct 1080p/720p/360p video downloads and Kwik embeds.
- **Aniwaves**: Vidplay HLS streams, DatSaV HD MP4 streams, and MyCloud servers.
- **KickAssAnime**: Vidstream master HLS playlists and multilingual soft-subs (English, Spanish, Portuguese, French, German, Arabic).
- **Anikoto**: High-speed Vidstream-2 and HD-2 master HLS streams.
- **Icarus**: UltraCloud HLS streams and downloads.

### 4. Keeply Proxy Stream Deobfuscation
Miruro proxies streaming segments through CDN endpoints (`https://s1.keeply.top/` and `https://s2.keeply.top/`).
- The segment URL path encodes the original upstream master `.m3u8` URL:
  `https://s2.keeply.top/{base64url_segment}/pl.m3u8`
- **Deobfuscator**:
  - Base64url decodes the segment.
  - XORs with `PROXY_OBF_KEY` (`a54d389c18527d9fd3e7f0643e27edbe`).
  - Recovers the raw direct upstream streaming URL (e.g., `https://fetch.nexabloom.top/anime/.../master.m3u8?token=...`).

### 5. DNS Poisoning & ISP Blocking Bypass
- In certain regions (such as India), ISPs poison domain resolutions for anime sites by returning `13.127.247.216` (DoT blocking page).
- The client integrates Cloudflare DoH resolution directly with `curl_cffi` via `CurlOpt.RESOLVE` mapping (`104.21.88.155`, `172.67.185.198`), ensuring 100% reliable connectivity.

---

## CLI Usage

### Search Anime
```bash
python -m anime.miruro.cli --search "Solo Leveling"
python -m anime.miruro.cli --search "Naruto" --limit 10
```

### Get Anime Details & Episode Catalog
```bash
python -m anime.miruro.cli --info "mxgbmPBIfqFpcH6qk0NmYu4n4eqpAiTH"
python -m anime.miruro.cli --info "https://www.miruro.cx/info/ZkbbIfGqvoOrvvss5iQuAlVkW4AaYPxz/one-piece"
```

### Extract Decrypted Video Streaming Sources & Subtitles
```bash
python -m anime.miruro.cli --episode "ZkbbIfGqvoOrvvss5iQuAlVkW4AaYPxz" --ep 1180
python -m anime.miruro.cli --episode "mxgbmPBIfqFpcH6qk0NmYu4n4eqpAiTH" --ep 1
```

### Crawl Series to SQLite Database
```bash
python -m anime.miruro.cli --crawl "mxgbmPBIfqFpcH6qk0NmYu4n4eqpAiTH" --max-episodes 5
```

### View Database Stats & Export to JSON
```bash
python -m anime.miruro.cli --stats
python -m anime.miruro.cli --export "mxgbmPBIfqFpcH6qk0NmYu4n4eqpAiTH"
```
