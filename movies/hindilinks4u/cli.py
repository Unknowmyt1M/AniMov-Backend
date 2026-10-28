"""Command-line interface for Hindilinks4u Movie Scraper."""

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
    from .scraper import Hindilinks4uScraper
    from .storage import Hindilinks4uStorage
except ImportError:
    from movies.hindilinks4u.scraper import Hindilinks4uScraper
    from movies.hindilinks4u.storage import Hindilinks4uStorage


def safe_str(val: Optional[str]) -> str:
    """Ensure safe string printing."""
    if not val:
        return "N/A"
    return str(val)


def print_search_results(results):
    if not results:
        console.print("\n[yellow]⚠️  No movies found.[/yellow]\n")
        return

    table = create_table(
        title=f"✨ Hindilinks4u Search Results ({len(results)}) ✨",
        columns=[
            ("Title", {"style": "bold bright_white"}),
            ("Year", {"style": "bright_green", "justify": "center"}),
            ("Type", {"style": "bright_yellow", "justify": "center"}),
            ("Quality", {"style": "bright_cyan", "justify": "center"}),
            ("Slug", {"style": "cyan"}),
        ],
        border_style="bright_blue",
        header_style="bold bright_magenta",
    )

    for item in results:
        type_badge = f"[bold on dark_blue] {safe_str(item.media_type).upper()} [/]"
        table.add_row(
            safe_str(item.title),
            safe_str(item.release_year),
            type_badge,
            safe_str(item.quality),
            item.slug,
        )

    console.print(table)


def print_movie_details(detail, show_all: bool = False, limit: int = 50):
    if not detail:
        console.print("\n[red]❌ Movie not found or failed to fetch.[/red]\n")
        return

    genres_str = " • ".join(f"[bold bright_magenta]{g}[/]" for g in detail.genres) if detail.genres else "[dim]N/A[/dim]"
    directors_str = ", ".join(detail.directors) if detail.directors else "[dim]N/A[/dim]"
    cast_str = ", ".join(detail.cast[:5]) if detail.cast else "[dim]N/A[/dim]"

    info = f"""[bold bright_white]🎬 Title:[/bold bright_white]        [bold bright_yellow]{detail.title}[/bold bright_yellow]
[bold bright_white]📺 Type:[/bold bright_white]         [bold on dark_blue] {safe_str(detail.media_type).upper()} [/]
[bold bright_white]📅 Release Year:[/bold bright_white] [bright_green]{safe_str(detail.release_year)}[/bright_green]
[bold bright_white]🌏 Country:[/bold bright_white]      [dim]{safe_str(detail.country)}[/dim]
[bold bright_white]🎬 Directors:[/bold bright_white]    [bright_cyan]{directors_str}[/bright_cyan]
[bold bright_white]👥 Cast:[/bold bright_white]         [dim]{cast_str}[/dim]
[bold bright_white]🎭 Genres:[/bold bright_white]       {genres_str}
[bold bright_white]🖥️  Streams:[/bold bright_white]      [bold bright_green]{len(detail.streams)} server(s)[/bold bright_green]

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
    parser = argparse.ArgumentParser(description="Hindilinks4u Movie Scraper CLI")
    parser.add_argument("--search", "-s", type=str, nargs="?", const="", default=None, help="Search for movies by title")
    parser.add_argument("--detail", "-d", type=str, help="Get full details by movie slug or URL")
    parser.add_argument("--stream", type=str, help="Extract streaming embed links for a movie")
    parser.add_argument("--all", "-a", action="store_true", help="Show all links without truncating")
    parser.add_argument("--limit", type=int, default=50, help="Display limit for streams (default: 50)")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--no-cache", action="store_true", help="Bypass SQLite cache")

    args = parser.parse_args()
    scraper = Hindilinks4uScraper()
    use_cache = not args.no_cache

    print_banner("HindiLinks4u", "Hindi & Dubbed Movies Streaming Scraper")

    try:
        if args.stats:
            storage = Hindilinks4uStorage()
            stats = storage.get_stats()
            content = f"""[bold bright_white]🔍 Cached Searches:[/bold bright_white] [bold cyan]{stats['cached_searches']}[/bold cyan]
[bold bright_white]🎬 Cached Movies:[/bold bright_white]   [bold green]{stats['cached_movies']}[/bold green]"""
            console.print(
                Panel(
                    content.strip(),
                    title="[bold bright_magenta]✦ Hindilinks4u Cache Stats ✦[/bold bright_magenta]",
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
            with status_spinner(f"Searching Hindilinks4u for '{args.search}'..."):
                results = scraper.search(args.search, use_cache=use_cache)
            print_search_results(results)
            if not results:
                sys.exit(1)

        elif args.detail:
            with status_spinner(f"Fetching movie details for '{args.detail}'..."):
                detail = scraper.get_movie_detail(args.detail, use_cache=use_cache)
            print_movie_details(detail, show_all=args.all, limit=args.limit)
            if not detail:
                sys.exit(1)

        elif args.stream:
            with status_spinner(f"Extracting streams for '{args.stream}'..."):
                detail = scraper.get_movie_detail(args.stream, use_cache=use_cache)
            if not detail or not detail.streams:
                console.print("\n[yellow]⚠️  No streams found.[/yellow]\n")
                sys.exit(1)

            st_table = create_table(
                title=f"🖥️  Found {len(detail.streams)} Stream Mirror(s) for '{detail.title}'",
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
