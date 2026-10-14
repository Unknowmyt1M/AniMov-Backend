# Hindilinks4u Movie Scraper

Independent movie scraper for **Hindilinks4u** (`https://hindilinks4u.church`), discovered and curated from [The Best Couch Potato List (TBCPL)](https://github.com/N3rdmade/TBCPL).

## Features
- **Direct Search**: Search for movies with title, year, poster, and quality.
- **Rich Movie Details**: Extracts director, cast, genres, country, synopsis, and year.
- **Video Embed Players**: Directly extracts iframe players (`SpeedoStream`, `PlayHub`, etc.) and official YouTube trailers.
- **SQLite WAL Cache**: High-performance persistent caching with automatic TTL.
- **Anti-Bot Resilient**: Built with `curl_cffi` using Chrome TLS fingerprinting.
- **Windows Console Safe**: Pure ASCII output to prevent `cp1252` encoding crashes.

## CLI Usage

```bash
# Search for movies
python -m movies.hindilinks4u.cli --search "Avengers"

# Get movie details & embeds
python -m movies.hindilinks4u.cli --detail "avengers-infinity-war-2018-hindi-dubbed-Watch-online-full-movie"

# Extract stream embed links
python -m movies.hindilinks4u.cli --stream "avengers-infinity-war-2018-hindi-dubbed-Watch-online-full-movie"

# Show cache statistics
python -m movies.hindilinks4u.cli --stats
```
