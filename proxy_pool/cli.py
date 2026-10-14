"""CLI for inspecting and managing the Auto-Refreshing Proxy Pool."""

import time
import argparse
from typing import Optional
from curl_cffi import requests

from .manager import get_proxy_manager
from .config import config


def safe_str(val: Optional[any]) -> str:
    """ASCII safe string converter."""
    if val is None:
        return "N/A"
    return str(val).encode("ascii", "replace").decode("ascii")


def main():
    parser = argparse.ArgumentParser(description="AniMov Auto-Refreshing Proxy Pool CLI")
    parser.add_argument("--refresh", action="store_true", help="Trigger immediate fetch and validation")
    parser.add_argument("--status", action="store_true", help="Display current pool health & metrics")
    parser.add_argument("--test", type=str, help="Test a target URL using an alive proxy from the pool")
    parser.add_argument("--daemon", action="store_true", help="Run standing background refresher process")
    parser.add_argument("--limit", type=int, default=200, help="Max candidates to validate during refresh")

    args = parser.parse_args()
    mgr = get_proxy_manager()

    if args.refresh:
        print("\n[+] Triggering Proxy Pool Refresh Cycle...")
        count = mgr.refresh_pool(max_to_test=args.limit)
        print(f"[+] Refresh completed! Active working proxies in pool: {count}")
        stats = mgr.get_stats()
        print(f"[+] Average Latency: {stats['average_latency_ms']}ms\n")

    elif args.status:
        stats = mgr.get_stats()
        print("\n" + "=" * 60)
        print("          ANIMOV PROXY POOL STATUS")
        print("=" * 60)
        print(f"Active Working Proxies:   {stats['active_proxies']}")
        print(f"Average Target Latency:   {stats['average_latency_ms']} ms")
        print(f"Refresh Interval:         Every {stats['refresh_interval_minutes']} minutes")
        last_ref = stats["last_refreshed"]
        last_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_ref)) if last_ref else "Never"
        print(f"Last Refresh Timestamp:   {last_str}")
        print("-" * 60)
        print(f"{'#':<3} | {'Proxy URL':<28} | {'Latency':<10} | {'Verified Target'}")
        print("-" * 60)
        for idx, p in enumerate(stats["top_proxies"], 1):
            url = safe_str(p["proxy"])
            lat = f"{p['latency_ms']}ms" if p["latency_ms"] else "N/A"
            tgt = safe_str(p.get("target", "N/A"))
            print(f"{idx:<3} | {url:<28} | {lat:<10} | {tgt}")
        print("=" * 60 + "\n")

    elif args.test:
        proxy = mgr.get_proxy()
        if not proxy:
            print("[!] Pool is empty. Please run with --refresh first.")
            return

        target_url = args.test
        print(f"\n[+] Testing Target: {target_url}")
        print(f"[+] Routing through Proxy: {proxy}")
        t0 = time.time()
        try:
            s = requests.Session(impersonate="chrome124")
            r = s.get(target_url, proxies={"http": proxy, "https": proxy}, timeout=8.0)
            dur = round((time.time() - t0) * 1000)
            print(f"[+] Result: HTTP {r.status_code} (Length: {len(r.text)} bytes, Time: {dur}ms)")
            if r.status_code == 200:
                mgr.report_success(proxy)
                print("[+] Proxy verified & marked healthy in pool!")
            else:
                mgr.report_failure(proxy)
        except Exception as e:
            mgr.report_failure(proxy)
            print(f"[-] Request failed: {e}")

    elif args.daemon:
        print("\n[+] Starting AniMov Proxy Pool Daemon Refresher...")
        print(f"[+] Refresh cycle: Every {config.refresh_interval_minutes} minutes")
        mgr.start_background_refresher()
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            print("\n[!] Stopping daemon refresher...")
            mgr.stop_background_refresher()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
