# AnimeKhor Scraper

High-performance, production-ready crawler and metadata extractor for **AnimeKhor** (`https://animekhor.org/`).

## Architecture & Features

- **TLS Impersonation (`curl_cffi`)**: Uses Chrome 124 fingerprint and IPv4 resolution to seamlessly bypass Cloudflare and edge rate limits.
- **Base64 Multi-Server Decryption**: Decodes Base64 encoded mirror select tags (`select.mirror option`) into playable iframe embeds across 11+ providers (VidPlayer/Dailymotion, OK.ru, Rumble, DTube, TurboVid, CloudPlayer, FilePlayer, DaraPlayer, VGPlayer, AbyssPlayer).
- **Comprehensive Metadata**: Extracts title, native/alternate names, rating, studio, status, country, duration, genres, release dates, synopsis, and posters (bypassing SVG placeholders).
- **Episode Resolver**: Handles batch numbering, multi-season ranges (e.g. `217-243`), and sorts episodes in strict ascending chronological order.
- **SQLite WAL Storage**: ACID-compliant relational persistence (`data/animekhor.db`) with fast query performance and resumable crawlers.
- **Direct Stream Sniffer**: Uses Playwright CDP network interceptor to sniff `.m3u8` and `.mp4` video manifests.
- **Rich CLI**: Beautiful terminal interface with Windows UTF-8 console support.

## CLI Usage

### Search Series
```bash
python -m donghua.AnimeKhor.cli --search "Renegade Immortal"
```

### Get Series Details & Episode List
```bash
python -m donghua.AnimeKhor.cli --info "renegade-immortal"
```

### Extract Episode Mirrors & Download Links
```bash
python -m donghua.AnimeKhor.cli --episode "https://animekhor.org/renegade-immortal-episode-160-subtitles-english-indonesian/"
```

### Crawl Series to Database
```bash
python -m donghua.AnimeKhor.cli --crawl "renegade-immortal" --max-episodes 2
```

### View Database Stats & Export to JSON
```bash
python -m donghua.AnimeKhor.cli --stats
python -m donghua.AnimeKhor.cli --export "renegade-immortal"
```
