"""Command-Line Interface for Anikage Anime Scraper."""

import argparse
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .scraper import AnikageScraper

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console()


def print_search_results(results):
    if not results:
        console.print("[yellow]No anime found matching your query.[/yellow]")
        return

    table = Table(title=f"Anikage Anime Results ({len(results)})", header_style="bold magenta")
    table.add_column("Slug", style="cyan")
    table.add_column("Title", style="bold white")
    table.add_column("Format", style="green")
    table.add_column("Score", style="yellow")
    table.add_column("Status", style="blue")
    table.add_column("Genres", style="dim white")

    for r in results:
        table.add_row(
            r.slug,
            r.display_title,
            r.format or "TV",
            str(r.score) if r.score is not None else "N/A",
            r.status or "N/A",
            ", ".join(r.genres[:3]),
        )
    console.print(table)


def print_details(detail):
    info = f"""[bold cyan]Title:[/bold cyan] {detail.display_title}
[bold cyan]Romaji:[/bold cyan] {detail.romaji}
[bold cyan]Native:[/bold cyan] {detail.native or 'N/A'}
[bold cyan]Slug:[/bold cyan] {detail.slug}
[bold cyan]Format:[/bold cyan] {detail.format or 'TV'}
[bold cyan]Status:[/bold cyan] {detail.status or 'N/A'}
[bold cyan]Score:[/bold cyan] {detail.score if detail.score is not None else 'N/A'}
[bold cyan]Year:[/bold cyan] {detail.year or 'N/A'}
[bold cyan]Total Episodes:[/bold cyan] {detail.total_episodes}
[bold cyan]Genres:[/bold cyan] {', '.join(detail.genres) if detail.genres else 'N/A'}
[bold cyan]Synopsis:[/bold cyan] {(detail.synopsis[:250] + '...') if detail.synopsis else 'N/A'}
"""
    console.print(Panel(info, title=f"Anikage: {detail.display_title}", border_style="magenta"))

    if detail.episodes:
        table = Table(title=f"Episodes ({len(detail.episodes)})", header_style="bold cyan")
        table.add_column("Ep #", style="bold yellow", width=6)
        table.add_column("Title", style="white")
        table.add_column("Air Date", style="blue")
        table.add_column("Rating", style="green")

        for ep in detail.episodes:
            table.add_row(
                str(ep.number),
                ep.title or f"Episode {ep.number}",
                ep.air_date or "N/A",
                str(ep.rating) if ep.rating is not None else "N/A",
            )
        console.print(table)


def print_sources(sources):
    if not sources:
        console.print("[yellow]No stream sources found.[/yellow]")
        return

    table = Table(title=f"Streaming Sources ({len(sources)})", header_style="bold green")
    table.add_column("Provider", style="bold cyan")
    table.add_column("Quality", style="yellow")
    table.add_column("Type", style="magenta")
    table.add_column("Format", style="white")
    table.add_column("URL / Stream Token", style="blue")

    for s in sources:
        fmt = "HLS / M3U8" if s.is_m3u8 else "Direct Stream"
        table.add_row(
            s.provider_id,
            s.quality or "Auto",
            s.stream_type.upper(),
            fmt,
            s.url[:60] + "...",
        )
    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="Anikage Anime Scraper CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Search
    search_parser = subparsers.add_parser("search", help="Search anime")
    search_parser.add_argument("query", help="Anime title to search")
    search_parser.add_argument("--page", type=int, default=1, help="Page number")

    # Catalog
    cat_parser = subparsers.add_parser("catalog", help="Browse catalog")
    cat_parser.add_argument(
        "--sort",
        choices=["trending", "popularity", "updated"],
        default="trending",
        help="Sort criterion",
    )
    cat_parser.add_argument(
        "--format",
        choices=["TV", "MOVIE", "OVA"],
        default=None,
        help="Filter format",
    )
    cat_parser.add_argument("--page", type=int, default=1, help="Page number")

    # Detail
    detail_parser = subparsers.add_parser("detail", help="Get anime detail & episode catalog")
    detail_parser.add_argument("slug", help="Anime slug (e.g. 5xxCxNSHUK)")

    # Streams
    stream_parser = subparsers.add_parser("streams", help="Get episode stream sources")
    stream_parser.add_argument("slug", help="Anime slug")
    stream_parser.add_argument("episode", type=int, help="Episode number")
    stream_parser.add_argument("--lang", choices=["sub", "dub"], default="sub", help="Audio type")
    stream_parser.add_argument("--provider", default=None, help="Specific provider ID (koto, pam, etc.)")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    scraper = AnikageScraper()

    try:
        if args.command == "search":
            console.print(f"[bold magenta]Searching Anikage for:[/bold magenta] {args.query}")
            results = scraper.search(args.query, page=args.page)
            print_search_results(results)

        elif args.command == "catalog":
            console.print(f"[bold magenta]Browsing catalog:[/bold magenta] Sort={args.sort} (Page {args.page})")
            results = scraper.get_catalog(sort=args.sort, format_filter=args.format, page=args.page)
            print_search_results(results)

        elif args.command == "detail":
            console.print(f"[bold magenta]Fetching anime details for:[/bold magenta] {args.slug}")
            detail = scraper.get_detail(args.slug)
            print_details(detail)

        elif args.command == "streams":
            console.print(f"[bold magenta]Fetching stream sources for:[/bold magenta] {args.slug} Ep {args.episode} ({args.lang})")
            sources = scraper.get_stream_sources(args.slug, args.episode, lang=args.lang, provider=args.provider)
            print_sources(sources)

    finally:
        scraper.close()


if __name__ == "__main__":
    main()
