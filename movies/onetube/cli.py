"""Command-line interface for 1Tube Scraper."""

import sys
import argparse
from typing import Optional

from .scraper import OneTubeScraper
from .storage import OneTubeStorage


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def safe_str(val: Optional[str]) -> str:
    """Ensure safe ASCII printing for Windows cp1252 consoles."""
    if not val:
        return "N/A"
    return str(val)


def main():
    parser = argparse.ArgumentParser(description="1Tube Movie & TV Scraper CLI")
    parser.add_argument("--search", "-s", type=str, nargs="?", const="", default=None, help="Search for titles via 1Tube API")
    parser.add_argument("--detail", "-d", type=str, help="Get title details by TMDB ID or watch URL")
    parser.add_argument("--stream", type=str, help="Extract streaming mirrors for a TMDB ID")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--no-cache", action="store_true", help="Bypass SQLite cache")

    args = parser.parse_args()
    scraper = OneTubeScraper()
    use_cache = not args.no_cache

    try:
        if args.stats:
            storage = OneTubeStorage()
            stats = storage.get_stats()
            print("\n=== 1Tube Cache Stats ===")
            print(f"Cached Searches: {stats['cached_searches']}")
            print(f"Cached Titles:   {stats['cached_movies']}")
            return

        if args.search is not None:
            if not args.search.strip():
                print("No search query provided.")
                sys.exit(1)
            print(f"\nSearching 1Tube for: '{args.search}'...")
            results = scraper.search(args.search, use_cache=use_cache)
            if not results:
                print("No items found.")
                sys.exit(1)

            print(f"\nFound {len(results)} items:\n")
            print(f"{'#':<3} | {'Title':<45} | {'Year':<6} | {'Type':<10} | {'Score':<8} | {'TMDB ID'}")
            print("-" * 88)
            for idx, item in enumerate(results, 1):
                title = safe_str(item.title)[:43]
                year = safe_str(item.release_year)
                mtype = safe_str(item.media_type)
                score = safe_str(item.score)
                print(f"{idx:<3} | {title:<45} | {year:<6} | {mtype:<10} | {score:<8} | {item.id}")

        elif args.detail:
            print(f"\nFetching details for TMDB ID: '{args.detail}'...")
            detail = scraper.get_movie_detail(args.detail, use_cache=use_cache)
            if not detail:
                print("Item not found or failed to fetch.")
                sys.exit(1)

            print("\n" + "=" * 65)
            print(f"Title:        {safe_str(detail.title)}")
            if detail.original_title and detail.original_title != detail.title:
                print(f"Orig Title:   {safe_str(detail.original_title)}")
            if detail.tagline:
                print(f"Tagline:      {safe_str(detail.tagline)}")
            print(f"Type:         {safe_str(detail.media_type)}")
            print(f"Release Year: {safe_str(detail.release_year)}")
            print(f"Duration:     {safe_str(detail.duration)}")
            print(f"Rating:       {safe_str(detail.rating)} ({detail.vote_count} votes)")
            print(f"Genres:       {', '.join(detail.genres) if detail.genres else 'N/A'}")
            print(f"Poster:       {safe_str(detail.poster)}")
            print(f"Watch URL:    {detail.watch_url}")
            print(f"Streams:      {len(detail.streams)} server(s)")
            for idx, s in enumerate(detail.streams, 1):
                print(f"  [{idx}] {s.server_name:<15} ({s.source_type}): {s.embed_url}")
            print("-" * 65)
            print(f"Synopsis:     {safe_str(detail.synopsis)[:300]}...")
            print("=" * 65)

        elif args.stream:
            print(f"\nExtracting streams for TMDB ID: '{args.stream}'...")
            detail = scraper.get_movie_detail(args.stream, use_cache=use_cache)
            if not detail or not detail.streams:
                print("No streams found.")
                sys.exit(1)

            print(f"\nFound {len(detail.streams)} streaming mirrors:")
            for idx, s in enumerate(detail.streams, 1):
                print(f"  [{idx}] Server: {s.server_name}")
                print(f"      Embed URL: {s.embed_url}")
                print(f"      Type:      {s.source_type}")

        else:
            parser.print_help()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
