# AniMov Backend 🎬⚡

Production-grade, modular web scrapers, metadata extractors, and stream resolvers for Anime, Movies/Series, and Donghua/Cartoons.

## Architecture & Design
- **Multi-Category Structure**: Clean separation between `anime`, `movies`, and `donghua`.
- **Resilient Networking**: Upstream dynamic mirror domain resolution with fallback, browser TLS fingerprinting, exponential backoff retries, and headers spoofing.
- **Strong Typing**: Pydantic models for media metadata, episode trees, stream sources, and cloud download links.
- **Rich CLI Support**: Each module features an interactive terminal CLI with formatted tables and color status output.

---

## Supported Providers

### 1. Donghua & Cartoons (`donghua/`)
- **Animexin** (`donghua/animexin`):
  - Chinese Donghua titles, studios, networks, dual synopses.
  - Multi-mirror streams (16+ hosts), direct 1080p and 4K download links.
  - SQLite WAL persistence and SHA1 HTML caching.
- **Toonstream** (`donghua/toonstream`):
  - Multi-audio Cartoons and Donghua (Hindi, English, Tamil, Telugu).
  - Dynamic season/episode AJAX crawler.
  - Stream server extractors: RubyStream, FilesForever, AbyssPlayer, Cloudy.

### 2. Movies & Web Series (`movies/`)
- **HDHub4u** (`movies/hdhub4u`):
  - Fast search bypassing anti-bot redirects via Typesense cluster.
  - Bollywood, Hollywood, Dual Audio, and 4K UHD content.
  - Extracts cloud direct links: HubCloud, HubDrive, HubCDN, and GDRive links across 480p, 720p, 1080p, and 4K.

### 3. Anime (`anime/`)
- **Anikage** (`anime/anikage`):
  - Clean REST API endpoints for catalog discovery, episode lists, and ratings.
  - Multi-server stream extraction (SUB/DUB): Ken, Pam, Koto, Megg, Wave/Vidplay with HLS (`.m3u8`) and direct MP4.
- **AnimeSuge** (`anime/animesuge`):
  - Multi-page catalog search and episode extraction.
  - MegaPlay AES-256 cipher decryption for direct HLS master playlists.
- **Miruro** (`anime/miruro`):
  - Full catalog browsing, GraphQL/REST metadata, and stream resolvers.
- **ReAnime** (`anime/reanime`):
  - Catalog browsing and stream link extraction.
- **WatchAnimeWorld** (`anime/watchanimeworld`):
  - Direct search, episode listing, and multi-host stream resolution.

---

## Quick Start

### Installation
```bash
pip install httpx beautifulsoup4 lxml rich curl_cffi pydantic
```

### CLI Commands

```bash
# Toonstream (Donghua & Cartoons)
python -m donghua.toonstream.cli search "Ben 10"
python -m donghua.toonstream.cli detail "ben-10-alien-force"
python -m donghua.toonstream.cli streams "/episode/ben-10-alien-force-1x1/"

# HDHub4u (Movies & Series)
python -m movies.hdhub4u.cli search "Interstellar"
python -m movies.hdhub4u.cli detail "interstellar-2014-hindi-imax-bluray-full-movie"

# Anikage (Anime)
python -m anime.anikage.cli search "Chainsaw Man"
python -m anime.anikage.cli detail "uFxerMrwx6"
python -m anime.anikage.cli streams "uFxerMrwx6" 1 --lang sub
```
