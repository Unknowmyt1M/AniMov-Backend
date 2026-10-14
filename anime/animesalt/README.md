# AnimeSalt Scraper

Independent, production-grade scraper for **AnimeSalt** (`https://animesalt.cx/`).

## Highlights
- **Multi-Language Audio Provider**:
  - Specializes in Indian Regional Dubs: **Hindi, Tamil, Telugu, English, and Japanese**.
  - Decodes base64 payload from `multi-lang-plyr.php?data=...` into direct player URLs (AbyssPlayer, etc.).
- **Catalog & Episode Management**:
  - Full search and series page parsing (poster, synopsis, genres, year).
  - Episode numbering by season & episode (e.g. `solo-leveling-1x1`, `solo-leveling-2x13`).
- **Network Resilience**:
  - `curl_cffi` TLS impersonation with Cloudflare Anycast IP resolution.

## CLI Usage

```bash
# Search anime
python -m anime.animesalt.cli --search "Solo Leveling"

# Series detail & episodes
python -m anime.animesalt.cli --detail "solo-leveling"

# Episode multi-audio streams
python -m anime.animesalt.cli --episode "solo-leveling-1x1"

# Crawl series
python -m anime.animesalt.cli --crawl "solo-leveling" --max-episodes 3

# Cache stats
python -m anime.animesalt.cli --stats
```
