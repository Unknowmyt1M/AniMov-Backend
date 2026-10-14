# WatchAnimeWorld Scraper

Independent, production-grade scraper for **WatchAnimeWorld (Anime World India)** (`https://watchanimeworld.one/`).

## Highlights
- **Anime World India Regional Dubs**:
  - Caters to Hindi, Tamil, Telugu, and English anime and cartoon dubs.
  - Resolves player embeds (Zephyrix, multi-audio iframes).
- **Comprehensive Catalog**:
  - Search anime and cartoon movies (`/?s={query}`)
  - Series details, genres, poster, synopsis, and season/episode indexing (`/series/{slug}/`).
  - Episode player extraction (`/episode/{slug}/`).
- **Resilient Networking**:
  - `curl_cffi` TLS impersonation with Cloudflare Anycast IP resolution.

## CLI Usage

```bash
# Search anime/cartoon
python -m anime.watchanimeworld.cli --search "Samurai"

# Series detail & episodes
python -m anime.watchanimeworld.cli --detail "the-elusive-samurai"

# Episode streaming embed
python -m anime.watchanimeworld.cli --episode "the-elusive-samurai-2x1"

# Crawl series
python -m anime.watchanimeworld.cli --crawl "the-elusive-samurai" --max-episodes 3

# Cache stats
python -m anime.watchanimeworld.cli --stats
```
