# Anikage Scraper

Independent, production-grade scraper for **Anikage** (`https://anikage.cc/` or active mirror via remote domain resolver), providing modern Anime metadata, episode lists, and multi-server stream extraction (SUB/DUB).

## Highlights
- **Clean RESTful API Architecture**:
  - Uses direct backend endpoints (`/api/media/anime/browse`, `/api/media/anime/{slug}`, `/api/media/anime/{slug}/episodes`).
- **Dynamic Domain Resolution**:
  - Automatically queries the upstream domain resolver with fallback to `https://anikage.cc/`.
- **Comprehensive Episode & Stream Extraction**:
  - Complete episode listing with ratings, titles, air dates, and thumbnails.
  - Multi-server stream extraction: Ken, Pam, Koto, Megg, Wave (Vidplay) supporting HLS (m3u8) and direct MP4 streams.

## CLI Usage

```bash
# Search anime catalog
python -m anime.anikage.cli search "Chainsaw Man"

# Anime detail & episode list
python -m anime.anikage.cli detail "uFxerMrwx6"

# Extract stream sources for an episode (ep number & lang: sub/dub)
python -m anime.anikage.cli streams "uFxerMrwx6" 1 --lang sub
```
