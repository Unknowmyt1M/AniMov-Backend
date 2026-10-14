"""Thread-safe ProxyPoolManager with background auto-refresh and failover."""

import os
import json
import time
import threading
import logging
from typing import Optional, List, Dict, Any

from .config import config
from .fetcher import ProxyFetcher
from .validator import ProxyValidator

logger = logging.getLogger(__name__)


class ProxyPoolManager:
    """Manages the in-memory pool of verified active proxies."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._pool_lock = threading.Lock()
        self.active_pool: List[Dict[str, Any]] = []
        self._pool_index = 0
        self._bg_thread: Optional[threading.Thread] = None
        self._running = False
        self.last_refresh_time: Optional[float] = None
        self.fetcher = ProxyFetcher()
        self.validator = ProxyValidator()

        # Load cached proxies from disk immediately
        self._load_cache()
        self._initialized = True

    def _load_cache(self):
        """Load previously verified proxies from JSON cache if available."""
        if os.path.exists(config.cache_file):
            try:
                with open(config.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    proxies = data.get("proxies", [])
                    with self._pool_lock:
                        self.active_pool = proxies
                        self.last_refresh_time = data.get("updated_at")
                    logger.info(f"Loaded {len(proxies)} cached proxies from {config.cache_file}")
            except Exception as e:
                logger.warning(f"Failed to load proxy cache: {e}")

    def _save_cache(self):
        """Save verified proxies to JSON disk cache."""
        os.makedirs(os.path.dirname(config.cache_file), exist_ok=True)
        try:
            with self._pool_lock:
                data = {
                    "updated_at": time.time(),
                    "count": len(self.active_pool),
                    "proxies": self.active_pool,
                }
            with open(config.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save proxy cache: {e}")

    def get_proxy(self) -> Optional[str]:
        """Get the next working proxy from the pool (round-robin)."""
        with self._pool_lock:
            if not self.active_pool:
                return None
            self._pool_index = (self._pool_index + 1) % len(self.active_pool)
            return self.active_pool[self._pool_index]["proxy"]

    def report_success(self, proxy_url: str):
        """Record successful request using this proxy."""
        with self._pool_lock:
            for item in self.active_pool:
                if item["proxy"] == proxy_url:
                    item["success_count"] = item.get("success_count", 0) + 1
                    item["fail_streak"] = 0
                    break

    def report_failure(self, proxy_url: str):
        """Record failure and evict proxy if streak exceeds threshold."""
        with self._pool_lock:
            for item in list(self.active_pool):
                if item["proxy"] == proxy_url:
                    streak = item.get("fail_streak", 0) + 1
                    item["fail_streak"] = streak
                    if streak >= config.max_consecutive_failures:
                        logger.info(f"Evicting dead proxy: {proxy_url} (streak: {streak})")
                        self.active_pool.remove(item)
                        self._save_cache()
                    break

    def refresh_pool(self, max_to_test: int = 250) -> int:
        """Fetch fresh public proxies, validate in parallel, and update pool."""
        logger.info("Starting proxy pool refresh cycle...")
        t0 = time.time()

        raw_proxies = self.fetcher.fetch_all()
        if not raw_proxies:
            logger.warning("No proxies fetched from remote sources.")
            return len(self.active_pool)

        verified = self.validator.validate_batch(raw_proxies, max_to_test=max_to_test)
        if not verified:
            logger.warning("No target-verified proxies found in this cycle.")
            return len(self.active_pool)

        # Truncate to max pool size
        final_pool = verified[: config.max_pool_size]

        with self._pool_lock:
            self.active_pool = final_pool
            self.last_refresh_time = time.time()
            self._pool_index = 0

        self._save_cache()
        duration = time.time() - t0
        logger.info(f"Pool refreshed: {len(final_pool)} alive proxies ready (took {duration:.1f}s)")
        return len(final_pool)

    def start_background_refresher(self):
        """Start auto-refresh background daemon thread."""
        with self._pool_lock:
            if self._bg_thread and self._bg_thread.is_alive():
                return

            self._running = True

            def _refresh_loop():
                while self._running:
                    # If pool is empty or older than refresh interval
                    should_refresh = False
                    with self._pool_lock:
                        if not self.active_pool:
                            should_refresh = True
                        elif self.last_refresh_time:
                            age_mins = (time.time() - self.last_refresh_time) / 60
                            if age_mins >= config.refresh_interval_minutes:
                                should_refresh = True

                    if should_refresh:
                        try:
                            self.refresh_pool()
                        except Exception as e:
                            logger.error(f"Error during background refresh: {e}")

                    # Sleep 60 seconds between checks
                    time.sleep(60)

            self._bg_thread = threading.Thread(target=_refresh_loop, daemon=True)
            self._bg_thread.start()
            logger.info("Proxy pool background refresher thread started.")

    def stop_background_refresher(self):
        """Stop background daemon thread."""
        self._running = False

    def get_stats(self) -> Dict[str, Any]:
        """Return pool health metrics."""
        with self._pool_lock:
            count = len(self.active_pool)
            avg_lat = 0
            if count > 0:
                avg_lat = sum(p.get("latency_ms", 0) for p in self.active_pool) / count
            return {
                "active_proxies": count,
                "average_latency_ms": round(avg_lat),
                "last_refreshed": self.last_refresh_time,
                "refresh_interval_minutes": config.refresh_interval_minutes,
                "top_proxies": [
                    {
                        "proxy": p["proxy"],
                        "latency_ms": p.get("latency_ms"),
                        "target": p.get("target_passed"),
                    }
                    for p in self.active_pool[:5]
                ],
            }


# Shared singleton getter
def get_proxy_manager() -> ProxyPoolManager:
    return ProxyPoolManager()
