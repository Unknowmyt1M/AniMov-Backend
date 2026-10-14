# AniMov Auto-Refreshing Proxy Pool (Option A)

High-performance, automated zero-cost ($0) proxy pool manager for AniMov scrapers and cloud deployments (Railway, Render, VPS).

## How It Works

```text
[Background Daemon / Cron (Every 30 Mins)]
            │
            ▼
[Fetch 400+ Free Proxies from Open APIs]
(ProxyScrape SSL, Monosans 30-min auto-sync, RoosterKid)
            │
            ▼
[Parallel Multi-Threaded Validation (35 Workers, 3.5s Timeout)]
Tests directly against real scraper endpoints (1Tube, Hindilinks4u)
            │
            ▼
[Memory Pool & Disk Cache (data/proxy_pool.json)]
Sorted by lowest latency (600ms - 1.8s)
            │
            ▼
[Scraper HTTP Requests] ─── Failover & Auto-Eviction of dead proxies
```

## Features
- **Zero Cost ($0)**: Auto-fetches from trusted public API mirrors.
- **Pre-Emptive Target Verification**: Filters out dead and transparent proxies; only keeps proxies that can actually bypass Cloudflare and scrape targets.
- **Failover & Eviction**: Automatically tracks consecutive failures; evicts dead proxies and switches to the next mirror instantly.
- **Daemon Auto-Refresher**: Refreshes pool in the background every 30 minutes without interrupting scrape requests.
- **Persistent Disk Cache**: Instant startup (`data/proxy_pool.json`) with zero initial latency.

## CLI Usage

```bash
# Trigger an immediate fetch and validation cycle
python -m proxy_pool.cli --refresh

# View active pool status, verified targets, and latencies
python -m proxy_pool.cli --status

# Test a live request routed through the proxy pool
python -m proxy_pool.cli --test "https://www.1tube.org/api/search?query=batman"

# Run standing background auto-refresher daemon
python -m proxy_pool.cli --daemon
```

## Python Integration in Scrapers

```python
from proxy_pool import get_proxy_manager

proxy_mgr = get_proxy_manager()
active_proxy = proxy_mgr.get_proxy()

if active_proxy:
    session.get(url, proxies={"http": active_proxy, "https": active_proxy})
```
