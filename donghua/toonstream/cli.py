"""Command-Line Interface for Toonstream Scraper."""

import argparse
import sys
from rich.panel import Panel

from common.ui import (
    console,
    print_banner,
    status_spinner,
    create_table,
    box,
)

try:
    from .scraper import ToonstreamScraper
except ImportError:
    from donghua.toonstream.scraper import ToonstreamScraper


def print_search_results(results):
    if not results:
        console.print("\n[yellow]⚠️  No items found.[/yellow]\n")
        return

    table = create_table(
        title=f"✨ Toonstream Results ({len(results)}) ✨",
        columns=[
            ("Slug", {"style": "cyan"}),
            ("Title", {"style": "bold bright_white"}),
            ("Type", {"style": "bright_green", "justify": "center"}),
            ("Score", {"style": "bright_yellow", "justify": "center"}),
            ("Link", {"style": "underline cyan"}),
        ],
        border_style="bright_blue",
        header_style="bold bright_magenta",
    )

    for r in results:
        type_badge = f"[bold on dark_blue] {r.media_type.upper()} [/]"
        score_val = f"⭐ {r.score}" if r.score else "N/A"
        table.add_row(
            r.slug,
            r.title,
            type_badge,
            score_val,
            r.link,
        )
    console.print(table)


def print_details(detail, show_all: bool = False, limit: int = 50):
    if not detail:
        console.print("\n[red]❌ Could not retrieve details.[/red]\n")
        return

    genres_str = " • ".join(f"[bold bright_magenta]{g}[/]" for g in detail.genres) if detail.genres else "[dim]N/A[/dim]"
    cast_str = ", ".join(detail.cast[:5]) if detail.cast else "[dim]N/A[/dim]"

    info = f"""[bold bright_white]🎬 Title:[/bold bright_white]         [bold bright_yellow]{detail.title}[/bold bright_yellow]
[bold bright_white]🔖 Slug:[/bold bright_white]          [cyan]{detail.slug}[/cyan]
[bold bright_white]📺 Type:[/bold bright_white]          [bold on dark_blue] {detail.media_type.upper()} [/]
[bold bright_white]⏱️  Duration:[/bold bright_white]      [bright_green]{detail.duration or 'N/A'}[/bright_green]
[bold bright_white]👥 Cast:[/bold bright_white]          [dim]{cast_str}[/dim]
[bold bright_white]🎭 Genres:[/bold bright_white]        {genres_str}

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

    if detail.media_type == "series" and detail.seasons:
        for s in detail.seasons:
            ep_list = s.episodes if show_all else s.episodes[:limit]
            table = create_table(
                title=f"📺 {s.title} ({len(s.episodes)} Episodes Total{' - Showing First ' + str(limit) if not show_all and len(s.episodes) > limit else ''})",
                columns=[
                    ("Code", {"style": "bold bright_yellow", "justify": "center", "width": 8}),
                    ("Title", {"style": "bold bright_white"}),
                    ("Episode Link", {"style": "underline cyan"}),
                ],
                border_style="cyan",
                header_style="bold bright_cyan",
            )
            for ep in ep_list:
                table.add_row(ep.episode_code, ep.title, ep.link)

            if not show_all and len(s.episodes) > limit:
                remaining = len(s.episodes) - limit
                table.add_row("...", f"[dim italic]+ {remaining} more episodes (use --all to show all)[/dim italic]", "...")

            console.print(table)
    elif detail.movie_streams:
        print_stream_servers(detail.movie_streams)


def print_stream_servers(servers):
    if not servers:
        console.print("\n[yellow]⚠️  No streaming servers found.[/yellow]\n")
        return

    table = create_table(
        title=f"🖥️  Available Streaming Servers ({len(servers)})",
        columns=[
            ("Server", {"style": "bold bright_white"}),
            ("Embed URL", {"style": "underline cyan"}),
            ("Resolved Inner Player", {"style": "bright_green"}),
        ],
        border_style="bright_green",
        header_style="bold bright_green",
    )

    for s in servers:
        table.add_row(
            s.server_name,
            s.embed_url,
            s.inner_iframe_url or "[dim]Direct[/dim]",
        )
    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="Toonstream Media Scraper CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Search
    search_parser = subparsers.add_parser("search", help="Search for series or movies")
    search_parser.add_argument("query", help="Title to search")
    search_parser.add_argument("--page", type=int, default=1, help="Page number")

    # Catalog
    cat_parser = subparsers.add_parser("catalog", help="Browse catalog category")
    cat_parser.add_argument(
        "--category",
        choices=["series", "category/cartoon", "category/anime", "category/movies"],
        default="series",
        help="Category to browse",
    )
    cat_parser.add_argument("--page", type=int, default=1, help="Page number")

    # Detail
    detail_parser = subparsers.add_parser("detail", help="Get series or movie details")
    detail_parser.add_argument("slug", help="Slug or URL of the title")
    detail_parser.add_argument("--all", "-a", action="store_true", help="Show all episodes without truncating")
    detail_parser.add_argument("--limit", type=int, default=50, help="Episode table display limit (default: 50)")

    # Streams
    stream_parser = subparsers.add_parser("streams", help="Get stream server links for episode or movie")
    stream_parser.add_argument("url", help="Episode or movie URL/path")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    print_banner("ToonStream", "Cartoons, Anime & Movies Streaming Scraper")

    scraper = ToonstreamScraper()

    try:
        if args.command == "search":
            with status_spinner(f"Searching Toonstream for '{args.query}'..."):
                results = scraper.search(args.query, page=args.page)
            print_search_results(results)

        elif args.command == "catalog":
            with status_spinner(f"Browsing category '{args.category}' (Page {args.page})..."):
                results = scraper.get_catalog(args.category, page=args.page)
            print_search_results(results)

        elif args.command == "detail":
            with status_spinner(f"Fetching details for '{args.slug}'..."):
                detail = scraper.get_detail(args.slug)
            print_details(detail, show_all=getattr(args, "all", False), limit=getattr(args, "limit", 50))

        elif args.command == "streams":
            with status_spinner(f"Extracting streaming servers for '{args.url}'..."):
                servers = scraper.get_stream_servers(args.url)
            print_stream_servers(servers)

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        sys.exit(1)
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
