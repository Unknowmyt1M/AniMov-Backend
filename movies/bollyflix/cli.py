"""Command-line interface for BollyFlix Movie Scraper."""

import sys
import argparse
from typing import Optional

from .scraper import BollyflixScraper
from .storage import BollyflixStorage


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def safe_str(val: Optional[str]) -> str:
    """Ensure safe string printing."""
    if not val:
        return "N/A"
    return str(val)


def main():
    parser = argparse.ArgumentParser(description="BollyFlix Movie Scraper CLI")
    parser.add_argument("--search", "-s", nargs="?", const="", default=None, help="Search for movies/series by title")
    parser.add_argument("--detail", "-d", type=str, help="Get full details by title slug or URL")
    parser.add_argument("--stream", type=str, help="Extract download / stream links for a title")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--no-cache", action="store_true", help="Bypass SQLite cache")

    args = parser.parse_args()
    scraper = BollyflixScraper()
    use_cache = not args.no_cache

    if args.stats:
        storage = BollyflixStorage()
        stats = storage.get_stats()
        print("\n=== BollyFlix Cache Stats ===")
        print(f"Cached Searches: {stats['cached_searches']}")
        print(f"Cached Titles:   {stats['cached_movies']}")
        return

    try:
        if args.search is not None:
            print(f"\nSearching BollyFlix for: '{args.search}'...")
            results = scraper.search(args.search, use_cache=use_cache)
            if not results:
                print("No items found.")
                sys.exit(1)

            print(f"\nFound {len(results)} items:\n")
            print(f"{'#':<3} | {'Slug':<42} | {'Title':<45} | {'Year':<6} | {'Type':<10} | {'Qualities'}")
            print("-" * 125)
            for idx, item in enumerate(results, 1):
                slug = safe_str(item.slug)[:40]
                title = safe_str(item.title)[:43]
                year = safe_str(item.release_year)
                mtype = safe_str(item.media_type)
                quals = ", ".join(item.qualities[:4]) if item.qualities else "N/A"
                print(f"{idx:<3} | {slug:<42} | {title:<45} | {year:<6} | {mtype:<10} | {quals}")

        elif args.detail:
            print(f"\nFetching details for: '{args.detail}'...")
            detail = scraper.get_movie_detail(args.detail, use_cache=use_cache)
            if not detail:
                print("Item not found or failed to fetch.")
                sys.exit(1)

            print("\n" + "=" * 65)
            print(f"Title:        {safe_str(detail.title)}")
            print(f"Type:         {safe_str(detail.media_type)}")
            print(f"Release Year: {safe_str(detail.release_year)}")
            print(f"Rating:       {safe_str(detail.rating)}")
            print(f"Languages:    {', '.join(detail.languages) if detail.languages else 'N/A'}")
            print(f"Subtitles:    {safe_str(detail.subtitles)}")
            print(f"Genres:       {', '.join(detail.genres) if detail.genres else 'N/A'}")
            print(f"Poster:       {safe_str(detail.poster)}")
            print(f"Downloads:    {len(detail.downloads)} link(s) available")
            for idx, d in enumerate(detail.downloads[:6], 1):
                lbl = safe_str(d.label)[:30]
                print(f"  [{idx}] {d.quality:<6} | {safe_str(d.size):<10} | {lbl:<30} -> {d.url}")
            print("-" * 65)
            print(f"Synopsis:     {safe_str(detail.synopsis)[:300]}...")
            print("=" * 65)

        elif args.stream:
            print(f"\nExtracting download / stream links for: '{args.stream}'...")
            detail = scraper.get_movie_detail(args.stream, use_cache=use_cache)
            if not detail or not detail.downloads:
                print("No links found.")
                sys.exit(1)

            print(f"\nFound {len(detail.downloads)} links:")
            for idx, d in enumerate(detail.downloads, 1):
                lbl = safe_str(d.label)
                print(f"  [{idx}] Quality: {d.quality}")
                print(f"      Size:    {safe_str(d.size)}")
                print(f"      Label:   {lbl}")
                print(f"      URL:     {d.url}")

        else:
            parser.print_help()

    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"\n[BollyFlix Error] {e}")
        print("(Note: If the BollyFlix domain is unreachable or blocked by your ISP, update base_url in config or verify network access.)")
        sys.exit(1)


if __name__ == "__main__":
    main()
