"""Command-line interface for Hindilinks4u Movie Scraper."""

import sys
import argparse
from typing import Optional

from .scraper import Hindilinks4uScraper
from .storage import Hindilinks4uStorage


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
    parser = argparse.ArgumentParser(description="Hindilinks4u Movie Scraper CLI")
    parser.add_argument("--search", "-s", type=str, nargs="?", const="", default=None, help="Search for movies by title")
    parser.add_argument("--detail", "-d", type=str, help="Get full details by movie slug or URL")
    parser.add_argument("--stream", type=str, help="Extract streaming embed links for a movie")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--no-cache", action="store_true", help="Bypass SQLite cache")

    args = parser.parse_args()
    scraper = Hindilinks4uScraper()
    use_cache = not args.no_cache

    try:
        if args.stats:
            storage = Hindilinks4uStorage()
            stats = storage.get_stats()
            print("\n=== Hindilinks4u Cache Stats ===")
            print(f"Cached Searches: {stats['cached_searches']}")
            print(f"Cached Movies:   {stats['cached_movies']}")
            return

        if args.search is not None:
            if not args.search.strip():
                print("No search query provided.")
                sys.exit(1)
            print(f"\nSearching Hindilinks4u for: '{args.search}'...")
            results = scraper.search(args.search, use_cache=use_cache)
            if not results:
                print("No movies found.")
                sys.exit(1)

            print(f"\nFound {len(results)} movies:\n")
            print(f"{'#':<3} | {'Title':<45} | {'Year':<6} | {'Type':<8} | {'Quality':<8} | {'Slug'}")
            print("-" * 95)
            for idx, item in enumerate(results, 1):
                title = safe_str(item.title)[:43]
                year = safe_str(item.release_year)
                mtype = safe_str(item.media_type)
                qual = safe_str(item.quality)
                print(f"{idx:<3} | {title:<45} | {year:<6} | {mtype:<8} | {qual:<8} | {item.slug}")

        elif args.detail:
            print(f"\nFetching movie details for: '{args.detail}'...")
            detail = scraper.get_movie_detail(args.detail, use_cache=use_cache)
            if not detail:
                print("Movie not found or failed to fetch.")
                sys.exit(1)

            print("\n" + "=" * 65)
            print(f"Title:        {safe_str(detail.title)}")
            print(f"Type:         {safe_str(detail.media_type)}")
            print(f"Release Year: {safe_str(detail.release_year)}")
            print(f"Country:      {safe_str(detail.country)}")
            print(f"Genres:       {', '.join(detail.genres) if detail.genres else 'N/A'}")
            print(f"Directors:    {', '.join(detail.directors) if detail.directors else 'N/A'}")
            print(f"Cast:         {', '.join(detail.cast[:5]) if detail.cast else 'N/A'}")
            print(f"Poster:       {safe_str(detail.poster)}")
            print(f"Trailer:      {safe_str(detail.trailer_url)}")
            print(f"Streams:      {len(detail.streams)} server(s)")
            for idx, s in enumerate(detail.streams, 1):
                print(f"  [{idx}] {s.server_name}: {s.embed_url}")
            print("-" * 65)
            print(f"Synopsis:     {safe_str(detail.synopsis)[:300]}...")
            print("=" * 65)

        elif args.stream:
            print(f"\nExtracting streams for: '{args.stream}'...")
            detail = scraper.get_movie_detail(args.stream, use_cache=use_cache)
            if not detail or not detail.streams:
                print("No streams found.")
                sys.exit(1)

            print(f"\nFound {len(detail.streams)} stream mirrors:")
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
