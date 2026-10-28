"""Command-Line Interface for HDHub4u Scraper."""

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
    from .scraper import HDHub4uScraper
except ImportError:
    from movies.hdhub4u.scraper import HDHub4uScraper


def print_search_results(results):
    if not results:
        console.print("\n[yellow]⚠️  No movies or series found.[/yellow]\n")
        return

    table = create_table(
        title=f"✨ HDHub4u Results ({len(results)}) ✨",
        columns=[
            ("Slug", {"style": "cyan"}),
            ("Title", {"style": "bold bright_white"}),
            ("Type", {"style": "bright_green", "justify": "center"}),
            ("Quality", {"style": "bright_yellow", "justify": "center"}),
            ("Link", {"style": "underline cyan"}),
        ],
        border_style="bright_blue",
        header_style="bold bright_magenta",
    )

    for r in results:
        type_badge = f"[bold on dark_blue] {r.media_type.upper()} [/]"
        table.add_row(
            r.slug,
            r.title,
            type_badge,
            r.quality_tag or "HD",
            r.link,
        )
    console.print(table)


def print_details(detail, show_all: bool = False, limit: int = 50):
    if not detail:
        console.print("\n[red]❌ Could not retrieve details.[/red]\n")
        return

    info = f"""[bold bright_white]🎬 Title:[/bold bright_white] [bold bright_yellow]{detail.title}[/bold bright_yellow]
[bold bright_white]📺 Type:[/bold bright_white]  [bold on dark_blue] {detail.media_type.upper()} [/]
[bold bright_white]🔖 Slug:[/bold bright_white]  [cyan]{detail.slug}[/cyan]
[bold bright_white]🔗 Link:[/bold bright_white]  [underline cyan]{detail.link}[/underline cyan]
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

    if detail.movie_links:
        links_list = detail.movie_links if show_all else detail.movie_links[:limit]
        table = create_table(
            title=f"⬇️  Available Movie Links & Packs ({len(detail.movie_links)} Total{' - Showing First ' + str(limit) if not show_all and len(detail.movie_links) > limit else ''})",
            columns=[
                ("Label", {"style": "bold bright_white"}),
                ("Quality", {"style": "bright_cyan", "justify": "center", "width": 10}),
                ("Size", {"style": "bright_yellow", "justify": "center", "width": 12}),
                ("Provider", {"style": "bright_green", "justify": "center"}),
                ("URL", {"style": "underline cyan"}),
            ],
            border_style="bright_green",
            header_style="bold bright_green",
        )

        for l in links_list:
            table.add_row(
                l.label,
                l.quality or "HD",
                l.size or "N/A",
                l.provider,
                l.url,
            )

        if not show_all and len(detail.movie_links) > limit:
            remaining = len(detail.movie_links) - limit
            table.add_row("...", "...", "...", "...", f"[dim italic]+ {remaining} more links (use --all to show all)[/dim italic]")

        console.print(table)

    if detail.episodes:
        ep_list = detail.episodes if show_all else detail.episodes[:limit]
        table = create_table(
            title=f"📺 Episodes ({len(detail.episodes)} Total{' - Showing First ' + str(limit) if not show_all and len(detail.episodes) > limit else ''})",
            columns=[
                ("Episode", {"style": "bold bright_yellow", "width": 15}),
                ("Options / Links", {"style": "white"}),
            ],
            border_style="cyan",
            header_style="bold bright_cyan",
        )

        for ep in ep_list:
            links_str = " | ".join(f"[bold green][{l.provider}][/bold green] {l.label} ([cyan]{l.url}[/cyan])" for l in ep.links)
            table.add_row(ep.title, links_str)

        if not show_all and len(detail.episodes) > limit:
            remaining = len(detail.episodes) - limit
            table.add_row("...", f"[dim italic]+ {remaining} more episodes (use --all to show all)[/dim italic]")

        console.print(table)


def main():
    parser = argparse.ArgumentParser(description="HDHub4u Movies & Web Series Scraper CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Search
    search_parser = subparsers.add_parser("search", help="Search for movies or series")
    search_parser.add_argument("query", help="Title to search")
    search_parser.add_argument("--page", type=int, default=1, help="Page number")

    # Catalog
    cat_parser = subparsers.add_parser("catalog", help="Browse catalog category")
    cat_parser.add_argument(
        "--category",
        choices=["bollywood-movies", "hollywood-movies", "hindi-dubbed", "category/web-series", "animated-movies"],
        default="bollywood-movies",
        help="Category to browse",
    )
    cat_parser.add_argument("--page", type=int, default=1, help="Page number")

    # Detail
    detail_parser = subparsers.add_parser("detail", help="Get movie or series details and download links")
    detail_parser.add_argument("slug_or_url", help="Slug or URL of the title")
    detail_parser.add_argument("--all", "-a", action="store_true", help="Show all links without truncating")
    detail_parser.add_argument("--limit", type=int, default=50, help="Display limit (default: 50)")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    print_banner("HDHub4u", "Movies & Web Series Direct Links Scraper")

    scraper = HDHub4uScraper()

    try:
        if args.command == "search":
            with status_spinner(f"Searching HDHub4u for '{args.query}' (Page {args.page})..."):
                results = scraper.search(args.query, page=args.page)
            print_search_results(results)

        elif args.command == "catalog":
            with status_spinner(f"Browsing '{args.category}' (Page {args.page})..."):
                results = scraper.get_catalog(args.category, page=args.page)
            print_search_results(results)

        elif args.command == "detail":
            with status_spinner(f"Fetching details for '{args.slug_or_url}'..."):
                detail = scraper.get_detail(args.slug_or_url)
            print_details(detail, show_all=getattr(args, "all", False), limit=getattr(args, "limit", 50))

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
