# KMMovies Scraper

Independent movie and series scraper for **KMMovies** (`https://kmmovies.cyou`), discovered and curated from [The Best Couch Potato List (TBCPL)](https://github.com/N3rdmade/TBCPL).

## Features
- **Search Aggregator**: Bollywood, Hollywood, South Indian Dubbed, and Regional releases.
- **Ultra High Definition Formats**: Supports extraction of 2160p UHD, 4K HDR10, Dolby Vision (DoVi), REMUX, BluRay, and 1080p high-frame-rate encodes (60FPS / 144FPS).
- **Fast MagicLinks**: Direct mirror links with exact file size breakdowns (e.g. 516MB to 66GB).
- **SQLite WAL Cache**: Reduces network overhead with local WAL-mode database caching.
- **Windows Safe**: Pure ASCII CLI output.

## CLI Usage

```bash
# Search catalog
python -m movies.kmmovies.cli --search "Avengers"

# Title details and download resolutions
python -m movies.kmmovies.cli --detail "the-avengers-2012-dual-audio-hindi-english-download-2160p-uhd-hdr10-dv-remux-bluray"

# Extract stream / download links
python -m movies.kmmovies.cli --stream "the-avengers-2012-dual-audio-hindi-english-download-2160p-uhd-hdr10-dv-remux-bluray"

# Cache statistics
python -m movies.kmmovies.cli --stats
```
