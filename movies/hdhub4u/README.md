# HDHub4u Scraper

Independent, production-grade scraper for **HDHub4u** (`https://new7.hdhub4u.cl/` or active mirror via remote domain resolver), providing Movies, Web Series, and 4K content with dual-audio and direct cloud download links.

## Highlights
- **Dynamic Domain Resolution**:
  - Automatically fetches the active mirror domain dynamically from upstream JSON configuration.
- **Fast Typesense Search**:
  - Leverages the internal Typesense search cluster (`https://search.pingora.fyi/collections/post/documents/search`) used by HDHub4u for lightning-fast search without anti-bot blocks.
- **Direct Cloud Links**:
  - Extracts direct high-speed hosting endpoints: HubCloud, HubDrive, HubCDN, and GDRive direct downloads across multiple resolutions (480p, 720p, 1080p, 4K).

## CLI Usage

```bash
# Search movies and series
python -m movies.hdhub4u.cli search "Interstellar"

# Media details and cloud download links
python -m movies.hdhub4u.cli detail "interstellar-2014-hindi-imax-bluray-full-movie"
```
