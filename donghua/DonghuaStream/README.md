# DonghuaStream Scraper

High-performance, production-ready crawler and metadata extractor for **DonghuaStream** (`https://donghuastream.org/`).

## Architecture & Features

- **TLS Impersonation (`curl_cffi`)**: Uses Chrome 124 browser fingerprint and forces IPv4 resolution to prevent Cloudflare/LiteSpeed TLS drops and IPv6 routing hangs.
- **Base64 Mirror Decryption**: Automatically decodes Base64 server options (`select.mirror option`) into iframes/embed links for Dailymotion, Rumble, StreamPlay, OK.ru, VidHide, etc.
- **Batch & Part Episode Parsing**: Resolves `Part 2`, `Episode 04 & 05`, and multi-part releases into proper numerical ordering, sorted ascending.
- **SQLite WAL Storage**: Thread-safe ACID persistence (`data/donghuastream.db`) with relational tables for Series, Episodes, Mirrors, and Downloads.
- **Direct Stream Sniffer**: Uses Playwright CDP network interceptor to sniff `.m3u8` and `.mp4` video manifests.
- **Rich CLI**: Beautiful terminal interface with Windows UTF-8 console support.

## CLI Usage

### Search Series
```bash
python -m donghua.DonghuaStream.cli --search "Soul Land"
```

### Get Series Details & Episode List
```bash
python -m donghua.DonghuaStream.cli --info "100-000-years-of-refining-qi-yang-ascendant"
```

### Extract Episode Mirrors & Download Links
```bash
python -m donghua.DonghuaStream.cli --episode "https://donghuastream.org/100-000-years-of-refining-qi-yang-ascendant-part2/"
```

### Crawl Series to Database
```bash
python -m donghua.DonghuaStream.cli --crawl "100-000-years-of-refining-qi-yang-ascendant" --max-episodes 2
```

### View Database Stats & Export to JSON
```bash
python -m donghua.DonghuaStream.cli --stats
python -m donghua.DonghuaStream.cli --export "100-000-years-of-refining-qi-yang-ascendant"
```
