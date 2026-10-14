# MoviesMod Scraper

Independent movie and web series scraper for **MoviesMod** (`https://moviesmod.ai.in`), discovered and curated from [The Best Couch Potato List (TBCPL)](https://github.com/N3rdmade/TBCPL).

## Features
- **Search Catalog**: Fast search covering Hollywood, Bollywood, Dual/Multi Audio, and OTT Series.
- **Detailed Release Specs**: Extracts audio tracks (Hindi, English, etc.), resolutions (480p, 720p, 1080p, 4K), and IMDb rating.
- **Fast Download Links**: Extracts `modpro.blog` batch and fast server archive links with file sizes.
- **SQLite WAL Cache**: Caches searches and details with configurable TTL.
- **Anti-Bot Protection**: Powered by `curl_cffi` Chrome TLS impersonation.
- **Windows Safe**: 100% ASCII sanitized CLI output.

## CLI Usage

```bash
# Search for movies / series
python -m movies.moviesmod.cli --search "Batman"

# View title details and download links
python -m movies.moviesmod.cli --detail "download-the-batman-2022-dual-audio-hindi-english-480p-720p-1080p"

# Extract stream / download links
python -m movies.moviesmod.cli --stream "download-the-batman-2022-dual-audio-hindi-english-480p-720p-1080p"

# View cache statistics
python -m movies.moviesmod.cli --stats
```
