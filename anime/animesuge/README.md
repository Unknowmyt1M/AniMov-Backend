# AnimeSuge Scraper

Independent, production-grade scraper for **AnimeSuge** (`https://animesuge.cz/`).

## Highlights
- **Full Catalog & Detail Extraction**:
  - Direct search with multi-page support (`/filter?keyword={query}`)
  - Episode lists with sub/dub availability (`/ajax/episode/list/{anime_id}`)
  - Multiple streaming mirrors: Vidstream-2, HD-1, Vidstream-1beta (`/ajax/server/list?servers={server_param}`)
- **MegaPlay Stream Decryption**:
  - Automatically queries `/stream/getSourcesNew?id={player_id}`
  - Decrypts AES-256-CBC cipher payloads to extract direct master HLS `.m3u8`
  - Captures VTT subtitle tracks and skip timestamps (intro/outro).
- **DNS Resilience**:
  - Uses `curl_cffi` with Chrome 124 TLS fingerprinting and Cloudflare Anycast IP resolution.

## CLI Usage

```bash
# Search anime
python -m anime.animesuge.cli --search "One Piece"

# Series detail & episodes
python -m anime.animesuge.cli --detail "one-piece-odmau"

# Stream episode
python -m anime.animesuge.cli --episode "one-piece-odmau" --ep 1 --server-type sub

# Crawl episodes
python -m anime.animesuge.cli --crawl "one-piece-odmau" --max-episodes 2

# Cache stats
python -m anime.animesuge.cli --stats
```
