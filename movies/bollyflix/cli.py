"""Command-line interface for BollyFlix Movie Scraper."""

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
    from .scraper import BollyflixScraper
    from .storage import BollyflixStorage
except ImportError:
    from movies.bollyflix.scraper import BollyflixScraper
    from movies.bollyflix.storage import BollyflixStorage


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
        title=f"✨ BollyFlix Search Results ({len(results)}) ✨",
        columns=[
            ("Slug", {"style": "cyan"}),
            ("Title", {"style": "bold bright_white"}),
            ("Year", {"style": "bright_green", "justify": "center"}),
            ("Type", {"style": "bright_yellow", "justify": "center"}),
            ("Qualities", {"style": "bright_blue"}),
        ],
        border_style="bright_blue",
        header_style="bold bright_magenta",
    )

    for item in results:
        type_badge = f"[bold on dark_blue] {safe_str(item.media_type).upper()} [/]"
        quals = ", ".join(item.qualities[:4]) if item.qualities else "N/A"
        table.add_row(
            safe_str(item.slug),
            safe_str(item.title),
            safe_str(item.release_year),
            type_badge,
            quals,
        )

    console.print(table)


def print_movie_details(detail, show_all: bool = False, limit: int = 50):
    if not detail:
        console.print("\n[red]❌ Item not found or failed to fetch.[/red]\n")
        return

    languages_str = ", ".join(detail.languages) if detail.languages else "[dim]N/A[/dim]"
    genres_str = " • ".join(f"[bold bright_magenta]{g}[/]" for g in detail.genres) if detail.genres else "[dim]N/A[/dim]"
    rating_str = f"⭐ [bold bright_yellow]{detail.rating}[/bold bright_yellow]" if detail.rating else "[dim]N/A[/dim]"

    info = f"""[bold bright_white]🎬 Title:[/bold bright_white]        [bold bright_yellow]{detail.title}[/bold bright_yellow]
[bold bright_white]📺 Type:[/bold bright_white]         [bold on dark_blue] {safe_str(detail.media_type).upper()} [/]
[bold bright_white]📅 Release Year:[/bold bright_white] [bright_green]{safe_str(detail.release_year)}[/bright_green]
[bold bright_white]⭐ Rating:[/bold bright_white]       {rating_str}
[bold bright_white]🌐 Languages:[/bold bright_white]    [bright_cyan]{languages_str}[/bright_cyan]
[bold bright_white]💬 Subtitles:[/bold bright_white]    [white]{safe_str(detail.subtitles)}[/white]
[bold bright_white]🎭 Genres:[/bold bright_white]       {genres_str}
[bold bright_white]⬇️  Downloads:[/bold bright_white]    [bold bright_green]{len(detail.downloads)} link(s) available[/bold bright_green]

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

    if detail.downloads:
        dl_list = detail.downloads if show_all else detail.downloads[:limit]
        dl_table = create_table(
            title=f"⬇️  Download & Stream Links ({len(detail.downloads)} Total{' - Showing First ' + str(limit) if not show_all and len(detail.downloads) > limit else ''})",
            columns=[
                ("Quality", {"style": "bold bright_yellow", "justify": "center", "width": 10}),
                ("Size", {"style": "bright_green", "justify": "center", "width": 12}),
                ("Label", {"style": "bold bright_white"}),
                ("URL", {"style": "underline cyan"}),
            ],
            border_style="bright_green",
            header_style="bold bright_green",
        )

        for d in dl_list:
            dl_table.add_row(
                d.quality,
                safe_str(d.size),
                safe_str(d.label),
                d.url,
            )

        if not show_all and len(detail.downloads) > limit:
            remaining = len(detail.downloads) - limit
            dl_table.add_row("...", "...", f"[dim italic]+ {remaining} more links (use --all to show all)[/dim italic]", "...")

        console.print(dl_table)


def main():
    parser = argparse.ArgumentParser(description="BollyFlix Movie Scraper CLI")
    parser.add_argument("--search", "-s", nargs="?", const="", default=None, help="Search for movies/series by title")
    parser.add_argument("--detail", "-d", type=str, help="Get full details by title slug or URL")
    parser.add_argument("--stream", type=str, help="Extract download / stream links for a title")
    parser.add_argument("--all", "-a", action="store_true", help="Show all links without truncating")
    parser.add_argument("--limit", type=int, default=50, help="Display limit for links (default: 50)")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--no-cache", action="store_true", help="Bypass SQLite cache")

    args = parser.parse_args()
    scraper = BollyflixScraper()
    use_cache = not args.no_cache

    print_banner("BollyFlix", "Bollywood & Hollywood Movies & Series Scraper")

    if args.stats:
        storage = BollyflixStorage()
        stats = storage.get_stats()
        content = f"""[bold bright_white]🔍 Cached Searches:[/bold bright_white] [bold cyan]{stats['cached_searches']}[/bold cyan]
[bold bright_white]🎬 Cached Titles:[/bold bright_white]   [bold green]{stats['cached_movies']}[/bold green]"""
        console.print(
            Panel(
                content.strip(),
                title="[bold bright_magenta]✦ BollyFlix Cache Stats ✦[/bold bright_magenta]",
                border_style="bright_magenta",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        return

    try:
        if args.search is not None:
            if not args.search.strip():
                console.print("[yellow]⚠️  No search query provided.[/yellow]")
                sys.exit(1)
            with status_spinner(f"Searching BollyFlix for '{args.search}'..."):
                results = scraper.search(args.search, use_cache=use_cache)
            print_search_results(results)
            if not results:
                sys.exit(1)

        elif args.detail:
            with status_spinner(f"Fetching details for '{args.detail}'..."):
                detail = scraper.get_movie_detail(args.detail, use_cache=use_cache)
            print_movie_details(detail, show_all=args.all, limit=args.limit)
            if not detail:
                sys.exit(1)

        elif args.stream:
            with status_spinner(f"Extracting download/stream links for '{args.stream}'..."):
                detail = scraper.get_movie_detail(args.stream, use_cache=use_cache)
            if not detail or not detail.downloads:
                console.print("\n[yellow]⚠️  No links found.[/yellow]\n")
                sys.exit(1)

            dl_table = create_table(
                title=f"⬇️  Found {len(detail.downloads)} Link(s) for '{detail.title}'",
                columns=[
                    ("Quality", {"style": "bold bright_yellow", "justify": "center", "width": 10}),
                    ("Size", {"style": "bright_green", "justify": "center", "width": 12}),
                    ("Label", {"style": "bold bright_white"}),
                    ("URL", {"style": "underline cyan"}),
                ],
                border_style="bright_green",
                header_style="bold bright_green",
            )
            for d in detail.downloads:
                dl_table.add_row(d.quality, safe_str(d.size), safe_str(d.label), d.url)
            console.print(dl_table)

        else:
            parser.print_help()

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]❌ [BollyFlix Error] {e}[/red]")
        console.print("[dim](Note: If the BollyFlix domain is unreachable or blocked by your ISP, update base_url in config or verify network access.)[/dim]\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
