"""Command-Line Interface for Anikage Anime Scraper."""

import argparse
import sys
from typing import Optional

from common.ui import (
    console,
    print_banner,
    status_spinner,
    create_table,
    box,
)
from rich.panel import Panel
from rich.table import Table
from .scraper import AnikageScraper


def print_search_results(results):
    if not results:
        console.print("\n[yellow]⚠️  No anime found matching your query.[/yellow]\n")
        return

    table = create_table(
        title=f"✨ Anikage Anime Search Results ({len(results)}) ✨",
        columns=[
            ("Slug", {"style": "cyan"}),
            ("Title", {"style": "bold bright_white"}),
            ("Format", {"style": "bright_green", "justify": "center"}),
            ("Score", {"style": "bright_yellow", "justify": "center"}),
            ("Status", {"style": "bright_blue", "justify": "center"}),
            ("Genres", {"style": "dim white"}),
        ],
        border_style="bright_blue",
        header_style="bold bright_magenta",
    )

    for r in results:
        fmt_badge = f"[bold on dark_blue] {r.format or 'TV'} [/]"
        score_val = f"⭐ {r.score:.1f}" if r.score is not None else "N/A"
        table.add_row(
            r.slug,
            r.display_title,
            fmt_badge,
            score_val,
            r.status or "N/A",
            ", ".join(r.genres[:3]) if r.genres else "N/A",
        )
    console.print(table)


def print_details(detail):
    if not detail:
        console.print("\n[red]❌ Could not retrieve anime details.[/red]\n")
        return

    genres_str = " • ".join(f"[bold bright_magenta]{g}[/]" for g in detail.genres) if detail.genres else "[dim]N/A[/dim]"
    score_str = f"⭐ [bold bright_yellow]{detail.score:.1f}/10[/bold bright_yellow]" if detail.score is not None else "[dim]N/A[/dim]"
    studios_str = ", ".join(getattr(detail, "studios", [])) if getattr(detail, "studios", None) else "[dim]N/A[/dim]"

    card_content = f"""[bold bright_white]🎬 Title:[/bold bright_white]         [bold bright_yellow]{detail.display_title}[/bold bright_yellow]
[bold bright_white]🇯🇵 Romaji:[/bold bright_white]        [white]{detail.romaji}[/white]
[bold bright_white]🔖 Slug:[/bold bright_white]          [cyan]{detail.slug}[/cyan]
[bold bright_white]📺 Format:[/bold bright_white]        [bold on dark_blue] {detail.format or 'TV'} [/]
[bold bright_white]📡 Status:[/bold bright_white]        [bright_blue]{detail.status or 'N/A'}[/bright_blue]
[bold bright_white]⭐ Score:[/bold bright_white]         {score_str}
[bold bright_white]📅 Year:[/bold bright_white]          [bright_green]{detail.year or 'N/A'}[/bright_green]
[bold bright_white]🏢 Studios:[/bold bright_white]       {studios_str}
[bold bright_white]🎭 Genres:[/bold bright_white]        {genres_str}
[bold bright_white]🎞️  Episodes:[/bold bright_white]      [bold bright_cyan]{detail.total_episodes} Episodes Total[/bold bright_cyan]

[bold bright_white]📖 Synopsis:[/bold bright_white]
[italic white]{detail.synopsis if detail.synopsis else 'N/A'}[/italic white]
"""
    console.print(
        Panel(
            card_content.strip(),
            title=f"[bold bright_cyan]✦ {detail.display_title.upper()} ✦[/bold bright_cyan]",
            border_style="bright_cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    if detail.episodes:
        table = create_table(
            title=f"📺 Episodes ({len(detail.episodes)})",
            columns=[
                ("Ep #", {"style": "bold bright_yellow", "justify": "center", "width": 8}),
                ("Title", {"style": "bold bright_white"}),
                ("Air Date", {"style": "bright_blue", "justify": "center"}),
                ("Rating", {"style": "bright_green", "justify": "center"}),
            ],
            border_style="cyan",
            header_style="bold bright_cyan",
        )

        for ep in detail.episodes:
            rating_str = f"★ {ep.rating:.1f}" if ep.rating is not None else "N/A"
            table.add_row(
                str(ep.number),
                ep.title or f"Episode {ep.number}",
                ep.air_date or "N/A",
                rating_str,
            )
        console.print(table)


def print_sources(sources):
    if not sources:
        console.print("\n[yellow]⚠️  No streaming sources found.[/yellow]\n")
        return

    table = create_table(
        title=f"🚀 Streaming Sources ({len(sources)})",
        columns=[
            ("Provider", {"style": "bold bright_cyan", "width": 14}),
            ("Quality", {"style": "bold bright_yellow", "justify": "center", "width": 12}),
            ("Type", {"style": "magenta", "justify": "center", "width": 10}),
            ("Format", {"style": "bright_green", "width": 16}),
            ("Stream URL / Token", {"style": "underline bright_white"}),
        ],
        border_style="bright_green",
        header_style="bold bright_green",
    )

    for s in sources:
        fmt = "⚡ HLS / M3U8" if s.is_m3u8 else "▶ Direct Stream"
        type_badge = f"[bold on dark_magenta] {s.stream_type.upper()} [/]"
        table.add_row(
            s.provider_id,
            s.quality or "Auto",
            type_badge,
            fmt,
            s.url,
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
    print_banner("Anikage", "High-Performance AniList & Multi-Server Scraper")

    if not args.command:
        parser.print_help()
        return

    scraper = AnikageScraper()

    try:
        if args.command == "search":
            with status_spinner(f"[bold bright_cyan]🔍 Searching Anikage for '[bold white]{args.query}[/bold white]'...[/bold bright_cyan]", spinner="dots12"):
                results = scraper.search(args.query, page=args.page)
            print_search_results(results)

        elif args.command == "catalog":
            with status_spinner(f"[bold bright_magenta]✨ Browsing Anikage catalog (Sort={args.sort}, Page {args.page})...[/bold bright_magenta]", spinner="aesthetic"):
                results = scraper.get_catalog(sort=args.sort, format_filter=args.format, page=args.page)
            print_search_results(results)

        elif args.command == "detail":
            with status_spinner(f"[bold bright_magenta]✨ Fetching anime details for '[bold white]{args.slug}[/bold white]'...[/bold bright_magenta]", spinner="aesthetic"):
                detail = scraper.get_detail(args.slug)
            print_details(detail)

        elif args.command == "streams":
            with status_spinner(f"[bold bright_green]🚀 Resolving stream sources for '[bold white]{args.slug}[/bold white]' Ep {args.episode}...[/bold bright_green]", spinner="arc"):
                sources = scraper.get_stream_sources(args.slug, args.episode, lang=args.lang, provider=args.provider)
            print_sources(sources)

    finally:
        scraper.close()


if __name__ == "__main__":
    main()
