# AnimeXin Donghua Scraper

Powerful Python scraper for AnimeXin (`animexin.dev` / `animexin.vip` / `animexin.xyz`),
built by combining the proven patterns from your pre-built projects:

- `Scarper/anime-agent/scrapers/animexin.py` — search + detail selectors, mirror domains
- `Scarper/AniFy/Provider/Animexin/animexin_provider.py` — `select.mirror` base64 decode,
  `listupd` / `eplister` / `info-content` parsing, duplicate-title fix
- `Scarper/Donghua/lucifer_scraper/*` — production pipeline: HTML cache, SQLite resume,
  retries/backoff, concurrency, `#pembed` embed extraction, JSON export + validation

## Features

- Multi-domain fallback (`animexin.dev` → `vip` → `xyz`)
- Search (`/?s=`), catalog walk (`/anime/` pagination), single-URL mode
- Detail parsing: title, poster (`bigcover` / `wp-post-image` / `og:image`),
  synopsis, genres (`genxps`), rating/quality/audio (`info-content`),
  status/type (`infox spe`), episode list (`eplister li`, `clstyle` fallback)
- Episode parsing: `select.mirror` base64 → iframe URL, `#pembed` iframes,
  Dailymotion `embedUrl` / `geo` player rebuild, `video` tags; `tickcounter.com`
  placeholders skipped; dynamic provider classification
- Episode label parser (title wins over num cell, ranges, parts, special/movie/trailer)
- SQLite (WAL) resume: `discovered → detail_parsed → complete|partial|failed`
- On-disk HTML cache (`sha1(url).html`), `--refresh` / `--reset` / `--retry-failed`
- Threaded pipeline + optional Playwright browser fallback for JS-gated pages
- `output/animexin.json` export with validation (duplicate/bad URLs, providers)

## Quick start

```bash
cd Donghua/Animexin
pip install -r requirements.txt
# optional, for browser fallback:
playwright install chromium

# smoke test (search + 2 episodes)
python scraper.py --search "Martial Master" --max-episodes 2

# single anime
python scraper.py --url "https://animexin.dev/anime/martial-master/" --max-episodes 2

# catalog smoke test
python scraper.py --max-anime 3 --max-episodes 2

# full scrape
python scraper.py --all

# resume / refresh / retry
python scraper.py --all --refresh
python scraper.py --retry-failed --max-anime 10
python scraper.py --validate-only
```

## Output

`output/animexin.json`:

```json
{
  "source": "https://animexin.dev/",
  "scraped_at": "...",
  "stats": {"anime": 1, "episodes": 2, "servers": 4, "embeds": 6},
  "items": [{
    "title": "Martial Master", "poster_url": "...", "synopsis": "...",
    "genres": ["Action"], "rating": "8", "quality": ["HD"],
    "audio": ["English", "Indonesian"],
    "detail_page_url": "...", "status": "Ongoing", "type": "ONA",
    "episodes": [{
      "episode_number": 1, "episode_title": "...",
      "episode_page_url": "...",
      "embeds": [{"provider": "dailymotion", "url": "...", "server_label": "Server 1"}]
    }]
  }]
}
```

## Layout

```
scraper.py
config.example.json
animexin_scraper/
  config.py  models.py  utils.py  http_client.py
  parser.py  players.py  episode_parser.py
  discovery.py  storage.py  pipeline.py  exporter.py  browser.py
tests/
```
