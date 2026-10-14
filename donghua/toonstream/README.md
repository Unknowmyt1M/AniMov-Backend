# Toonstream Scraper

Independent, robust scraper for **Toonstream** (`https://toonstream.co/` or active mirror via remote domain resolver), supporting Cartoons, Anime, and Donghua in multiple languages (Hindi, English, Tamil, Telugu).

## Highlights
- **Dynamic Domain Resolution**:
  - Automatically queries the upstream domain resolver (`https://raw.githubusercontent.com/phisher98/TVVVV/refs/heads/main/domains.json`) for latest active domains with automatic fallback to `https://toonstream.co/`.
- **Full Catalog & Episode Extraction**:
  - Direct search with multi-page support (`/?s={query}`).
  - Media details including seasons, episodes, synopsis, release date, and poster artwork.
  - Multi-season support via dynamic season AJAX endpoint (`/wp-admin/admin-ajax.php?action=action_select_season`).
- **Stream Server Resolution**:
  - Automatically resolves embed mirrors: RubyStream, FilesForever, AbyssPlayer, Cloudy, etc.

## CLI Usage

```bash
# Search cartoon / donghua
python -m donghua.toonstream.cli search "Ben 10"

# Media details & full season / episode listing
python -m donghua.toonstream.cli detail "ben-10-alien-force"

# Extract stream servers for an episode
python -m donghua.toonstream.cli streams "/episode/ben-10-alien-force-1x1/"
```
