"""Command-Line Interface for HDHub4u Scraper."""

import argparse
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .scraper import HDHub4uScraper

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console()


def print_search_results(results):
    if not results:
        console.print("[yellow]No movies or series found.[/yellow]")
        return

    table = Table(title=f"HDHub4u Results ({len(results)})", header_style="bold cyan")
    table.add_column("Slug", style="cyan")
    table.add_column("Title", style="bold white")
    table.add_column("Type", style="green")
    table.add_column("Quality", style="yellow")
    table.add_column("Link", style="blue")

    for r in results:
        table.add_row(
            r.slug,
            r.title,
            r.media_type,
            r.quality_tag or "HD",
            r.link,
        )
    console.print(table)


def print_details(detail):
    info = f"""[bold cyan]Title:[/bold cyan] {detail.title}
[bold cyan]Type:[/bold cyan] {detail.media_type}
[bold cyan]Slug:[/bold cyan] {detail.slug}
[bold cyan]Link:[/bold cyan] {detail.link}
"""
    console.print(Panel(info, title=f"HDHub4u: {detail.title}", border_style="cyan"))

    if detail.movie_links:
        table = Table(title=f"Available Movie Links & Packs ({len(detail.movie_links)})", header_style="bold magenta")
        table.add_column("Label", style="white")
        table.add_column("Quality", style="cyan")
        table.add_column("Size", style="yellow")
        table.add_column("Provider", style="green")
        table.add_column("URL", style="blue")

        for l in detail.movie_links:
            table.add_row(
                l.label,
                l.quality or "HD",
                l.size or "N/A",
                l.provider,
                l.url,
            )
        console.print(table)

    if detail.episodes:
        table = Table(title=f"Episodes ({len(detail.episodes)})", header_style="bold green")
        table.add_column("Episode", style="cyan", width=12)
        table.add_column("Options / Links", style="white")

        for ep in detail.episodes:
            links_str = " | ".join(f"[{l.provider}] {l.label} ({l.url})" for l in ep.links)
            table.add_row(ep.title, links_str)
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

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    scraper = HDHub4uScraper()

    try:
        if args.command == "search":
            console.print(f"[bold cyan]Searching HDHub4u for:[/bold cyan] {args.query}")
            results = scraper.search(args.query, page=args.page)
            print_search_results(results)

        elif args.command == "catalog":
            console.print(f"[bold cyan]Browsing category:[/bold cyan] {args.category} (Page {args.page})")
            results = scraper.get_catalog(args.category, page=args.page)
            print_search_results(results)

        elif args.command == "detail":
            console.print(f"[bold cyan]Fetching details for:[/bold cyan] {args.slug_or_url}")
            detail = scraper.get_detail(args.slug_or_url)
            print_details(detail)

    finally:
        scraper.close()


if __name__ == "__main__":
    main()
