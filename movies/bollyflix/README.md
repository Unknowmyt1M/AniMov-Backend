# BollyFlix Movie & Series Scraper

Independent movie and web series scraper for **BollyFlix** (`https://new.bollyflix.vote`), discovered and curated from [The Best Couch Potato List (TBCPL)](https://github.com/N3rdmade/TBCPL).

## Features
- **Search Movies & Series**: Full search supporting multi-language audio (Dual Audio Hindi/English, South Dubbed, Bollywood, Hollywood).
- **Multi-Quality Resolution Extraction**: Detects 480p, 720p, 1080p, 2160p 4K, HDR, BluRay, and WEB-DL releases.
- **Fast Server & Direct Download Links**: Extracts download & fast-stream server landing links with file sizes.
- **SQLite WAL Cache**: Caching with configurable TTL to reduce network latency.
- **Chrome TLS Impersonation**: Bypasses Cloudflare protection using `curl_cffi`.
- **Windows CLI Safe**: Fully ASCII sanitized output.

## CLI Usage

```bash
# Search for titles
python -m movies.bollyflix.cli --search "Thunderbolts"

# View movie details and quality options
python -m movies.bollyflix.cli --detail "thunderbolts-aka-the-new-avengers-2025-dual-audio-hindi-english-movie"

# Extract stream / download links
python -m movies.bollyflix.cli --stream "thunderbolts-aka-the-new-avengers-2025-dual-audio-hindi-english-movie"

# Cache statistics
python -m movies.bollyflix.cli --stats
```
