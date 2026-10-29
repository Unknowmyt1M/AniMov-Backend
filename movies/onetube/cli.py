"""Command-line interface for 1Tube Scraper."""

import sys
import argparse
from typing import Optional
from rich.panel import Panel

from common.ui import (
    console,
    print_banner,
    status_spinner,
    create_table,
    box,
)

try:
    from .scraper import OneTubeScraper
    from .storage import OneTubeStorage
except ImportError:
    from movies.onetube.scraper import OneTubeScraper
    from movies.onetube.storage import OneTubeStorage


def safe_str(val: Optional[str]) -> str:
    """Ensure safe string printing."""
    if not val:
        return "N/A"
    return str(val)


def print_search_results(results):
    if not results:
        console.print("\n[yellow]⚠️  No items found.[/yellow]\n")
        return

    table = create_table(
        title=f"✨ 1Tube Search Results ({len(results)}) ✨",
        columns=[
            ("Title", {"style": "bold bright_white"}),
            ("Year", {"style": "bright_green", "justify": "center"}),
            ("Type", {"style": "bright_yellow", "justify": "center"}),
            ("Score", {"style": "bright_magenta", "justify": "center"}),
            ("TMDB ID", {"style": "cyan"}),
        ],
        border_style="bright_blue",
        header_style="bold bright_magenta",
    )

    for item in results:
        type_badge = f"[bold on dark_blue] {safe_str(item.media_type).upper()} [/]"
        score_val = f"⭐ {item.score}" if item.score else "N/A"
        table.add_row(
            safe_str(item.title),
            safe_str(item.release_year),
            type_badge,
            score_val,
            str(item.id),
        )

    console.print(table)


def print_movie_details(detail, show_all: bool = False, limit: int = 50):
    if not detail:
        console.print("\n[red]❌ Item not found or failed to fetch.[/red]\n")
        return

    genres_str = " • ".join(f"[bold bright_magenta]{g}[/]" for g in detail.genres) if detail.genres else "[dim]N/A[/dim]"
    rating_str = f"⭐ [bold bright_yellow]{detail.rating}[/bold bright_yellow] ([dim]{detail.vote_count} votes[/dim])" if detail.rating else "[dim]N/A[/dim]"
    orig_title_str = f"\n[bold bright_white]🇯🇵 Orig Title:[/bold bright_white]   [white]{detail.original_title}[/white]" if detail.original_title and detail.original_title != detail.title else ""
    tagline_str = f"\n[bold bright_white]💬 Tagline:[/bold bright_white]      [italic bright_cyan]\"{detail.tagline}\"[/italic bright_cyan]" if detail.tagline else ""

    info = f"""[bold bright_white]🎬 Title:[/bold bright_white]         [bold bright_yellow]{detail.title}[/bold bright_yellow]{orig_title_str}{tagline_str}
[bold bright_white]📺 Type:[/bold bright_white]          [bold on dark_blue] {safe_str(detail.media_type).upper()} [/]
[bold bright_white]📅 Release Year:[/bold bright_white]  [bright_green]{safe_str(detail.release_year)}[/bright_green]
[bold bright_white]⏱️  Duration:[/bold bright_white]      [bright_cyan]{safe_str(detail.duration)}[/bright_cyan]
[bold bright_white]⭐ Rating:[/bold bright_white]        {rating_str}
[bold bright_white]🎭 Genres:[/bold bright_white]        {genres_str}
[bold bright_white]🔗 Watch URL:[/bold bright_white]     [underline cyan]{detail.watch_url}[/underline cyan]
[bold bright_white]🖥️  Streams:[/bold bright_white]       [bold bright_green]{len(detail.streams)} server(s)[/bold bright_green]

[bold bright_white]📖 Synopsis:[/bold bright_white]
[italic white]{detail.synopsis.strip() if detail.synopsis else 'N/A'}[/italic white]
"""
    console.print(
        Panel(
            info.strip(),
            title=f"[bold bright_cyan]✦ {detail.title.upper()} ✦[/bold bright_cyan]",
            border_style="bright_cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    if detail.streams:
        st_list = detail.streams if show_all else detail.streams[:limit]
        st_table = create_table(
            title=f"🖥️  Streaming Mirrors ({len(detail.streams)} Total{' - Showing First ' + str(limit) if not show_all and len(detail.streams) > limit else ''})",
            columns=[
                ("Server", {"style": "bold bright_white"}),
                ("Embed URL", {"style": "underline cyan"}),
                ("Source Type", {"style": "bright_green", "justify": "center"}),
            ],
            border_style="bright_green",
            header_style="bold bright_green",
        )

        for s in st_list:
            st_table.add_row(
                s.server_name,
                s.embed_url,
                s.source_type or "embed",
            )

        if not show_all and len(detail.streams) > limit:
            remaining = len(detail.streams) - limit
            st_table.add_row("...", f"[dim italic]+ {remaining} more servers (use --all to show all)[/dim italic]", "...")

        console.print(st_table)


def main():
    parser = argparse.ArgumentParser(description="1Tube Movie & TV Scraper CLI")
    parser.add_argument("--search", "-s", type=str, nargs="?", const="", default=None, help="Search for titles via 1Tube API")
    parser.add_argument("--detail", "-d", type=str, help="Get title details by TMDB ID or watch URL")
    parser.add_argument("--type", "-t", type=str, choices=["movie", "tv"], default=None, help="Media type ('movie' or 'tv') for TMDB ID")
    parser.add_argument("--stream", type=str, help="Extract streaming mirrors for a TMDB ID")
    parser.add_argument("--all", "-a", action="store_true", help="Show all links without truncating")
    parser.add_argument("--limit", type=int, default=50, help="Display limit for streams (default: 50)")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--no-cache", action="store_true", help="Bypass SQLite cache")

    args = parser.parse_args()
    scraper = OneTubeScraper()
    use_cache = not args.no_cache

    print_banner("1Tube", "TMDB-Powered Movies & TV Streaming Scraper")

    try:
        if args.stats:
            storage = OneTubeStorage()
            stats = storage.get_stats()
            content = f"""[bold bright_white]🔍 Cached Searches:[/bold bright_white] [bold cyan]{stats['cached_searches']}[/bold cyan]
[bold bright_white]🎬 Cached Titles:[/bold bright_white]   [bold green]{stats['cached_movies']}[/bold green]"""
            console.print(
                Panel(
                    content.strip(),
                    title="[bold bright_magenta]✦ 1Tube Cache Stats ✦[/bold bright_magenta]",
                    border_style="bright_magenta",
                    box=box.ROUNDED,
                    padding=(1, 2),
                )
            )
            return

        if args.search is not None:
            if not args.search.strip():
                console.print("[yellow]⚠️  No search query provided.[/yellow]")
                sys.exit(1)
            with status_spinner(f"Searching 1Tube for '{args.search}'..."):
                results = scraper.search(args.search, use_cache=use_cache)
            print_search_results(results)
            if not results:
                sys.exit(1)

        elif args.detail:
            with status_spinner(f"Fetching details for TMDB ID '{args.detail}'..."):
                try:
                    detail = scraper.get_movie_detail(args.detail, media_type=args.type, use_cache=use_cache)
                except ValueError as e:
                    console.print(f"\n[red]❌ {e}[/red]\n[yellow]💡 Tip: Specify '--type tv' or '--type movie'[/yellow]\n")
                    sys.exit(1)
            print_movie_details(detail, show_all=args.all, limit=args.limit)
            if not detail:
                sys.exit(1)

        elif args.stream:
            with status_spinner(f"Extracting streams for TMDB ID '{args.stream}'..."):
                try:
                    detail = scraper.get_movie_detail(args.stream, media_type=args.type, use_cache=use_cache)
                except ValueError as e:
                    console.print(f"\n[red]❌ {e}[/red]\n[yellow]💡 Tip: Specify '--type tv' or '--type movie'[/yellow]\n")
                    sys.exit(1)
            if not detail or not detail.streams:
                console.print("\n[yellow]⚠️  No streams found.[/yellow]\n")
                sys.exit(1)

            st_table = create_table(
                title=f"🖥️  Found {len(detail.streams)} Streaming Mirror(s) for '{detail.title}'",
                columns=[
                    ("Server", {"style": "bold bright_white"}),
                    ("Embed URL", {"style": "underline cyan"}),
                    ("Source Type", {"style": "bright_green", "justify": "center"}),
                ],
                border_style="bright_green",
                header_style="bold bright_green",
            )
            for s in detail.streams:
                st_table.add_row(s.server_name, s.embed_url, s.source_type or "embed")
            console.print(st_table)

        else:
            parser.print_help()

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
