"""Command-Line Interface for Toonstream Scraper."""

import argparse
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .scraper import ToonstreamScraper

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console()


def print_search_results(results):
    if not results:
        console.print("[yellow]No items found.[/yellow]")
        return

    table = Table(title=f"Toonstream Results ({len(results)})", header_style="bold cyan")
    table.add_column("Slug", style="cyan")
    table.add_column("Title", style="bold white")
    table.add_column("Type", style="green")
    table.add_column("Score", style="yellow")
    table.add_column("Link", style="blue")

    for r in results:
        table.add_row(
            r.slug,
            r.title,
            r.media_type,
            r.score or "N/A",
            r.link,
        )
    console.print(table)


def print_details(detail):
    info = f"""[bold cyan]Title:[/bold cyan] {detail.title}
[bold cyan]Type:[/bold cyan] {detail.media_type}
[bold cyan]Slug:[/bold cyan] {detail.slug}
[bold cyan]Genres:[/bold cyan] {', '.join(detail.genres) if detail.genres else 'N/A'}
[bold cyan]Duration:[/bold cyan] {detail.duration or 'N/A'}
[bold cyan]Cast:[/bold cyan] {', '.join(detail.cast[:4]) if detail.cast else 'N/A'}
[bold cyan]Synopsis:[/bold cyan] {(detail.synopsis[:200] + '...') if detail.synopsis else 'N/A'}
"""
    console.print(Panel(info, title=f"Toonstream: {detail.title}", border_style="cyan"))

    if detail.media_type == "series" and detail.seasons:
        for s in detail.seasons:
            table = Table(title=f"{s.title} ({len(s.episodes)} episodes)", header_style="bold green")
            table.add_column("Code", style="cyan", width=8)
            table.add_column("Title", style="white")
            table.add_column("Episode Link", style="blue")
            for ep in s.episodes:
                table.add_row(ep.episode_code, ep.title, ep.link)
            console.print(table)
    elif detail.movie_streams:
        print_stream_servers(detail.movie_streams)


def print_stream_servers(servers):
    if not servers:
        console.print("[yellow]No streaming servers found.[/yellow]")
        return

    table = Table(title=f"Available Streaming Servers ({len(servers)})", header_style="bold magenta")
    table.add_column("Server", style="bold cyan")
    table.add_column("Embed URL", style="white")
    table.add_column("Resolved Inner Player", style="green")

    for s in servers:
        table.add_row(
            s.server_name,
            s.embed_url,
            s.inner_iframe_url or "Direct",
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

    # Streams
    stream_parser = subparsers.add_parser("streams", help="Get stream server links for episode or movie")
    stream_parser.add_argument("url", help="Episode or movie URL/path")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    scraper = ToonstreamScraper()

    try:
        if args.command == "search":
            console.print(f"[bold cyan]Searching Toonstream for:[/bold cyan] {args.query}")
            results = scraper.search(args.query, page=args.page)
            print_search_results(results)

        elif args.command == "catalog":
            console.print(f"[bold cyan]Browsing category:[/bold cyan] {args.category} (Page {args.page})")
            results = scraper.get_catalog(args.category, page=args.page)
            print_search_results(results)

        elif args.command == "detail":
            console.print(f"[bold cyan]Fetching details for:[/bold cyan] {args.slug}")
            detail = scraper.get_detail(args.slug)
            print_details(detail)

        elif args.command == "streams":
            console.print(f"[bold cyan]Extracting streaming servers for:[/bold cyan] {args.url}")
            servers = scraper.get_stream_servers(args.url)
            print_stream_servers(servers)

    finally:
        scraper.close()


if __name__ == "__main__":
    main()
