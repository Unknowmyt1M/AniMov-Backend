# 1Tube Movie & TV Scraper

Independent movie and TV scraper for **1Tube** (`https://www.1tube.org`), discovered and curated from [The Best Couch Potato List (TBCPL)](https://github.com/N3rdmade/TBCPL).

## Features
- **JSON Search API**: Direct querying of 1Tube's backend API (`/api/search`) with full TMDB IDs, release dates, posters, and vote ratings.
- **Deep Metadata**: Fetches `/api/details/{id}` for rich taglines, durations, vote counts, backdrop URLs, and genre categorizations.
- **Multi-Server Streaming**: Extracts Layla player embeds from `/watch/{id}` alongside fallback mirrors (`VidSrc`, `2Embed`, `AutoEmbed`).
- **SQLite WAL Cache**: Reduces network calls with automated TTL caching.
- **Windows CLI Safe**: Fully sanitized ASCII output.

## CLI Usage

```bash
# Search for movies / TV shows
python -m movies.onetube.cli --search "Avengers Endgame"

# Fetch details by TMDB ID
python -m movies.onetube.cli --detail 299534

# Extract streaming embed mirrors
python -m movies.onetube.cli --stream 299534

# View cache statistics
python -m movies.onetube.cli --stats
```
