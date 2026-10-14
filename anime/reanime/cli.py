"""Rich Command-Line Interface for ReAnime Scraper."""

import argparse
import sys
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .scraper import ReAnimeScraper
from .storage import ReAnimeStorage

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

    table = Table(title=f"ReAnime Search Results ({len(results)})", header_style="bold magenta")
    table.add_column("Slug", style="cyan", no_wrap=False, overflow="fold")
    table.add_column("Title", style="bold white")
    table.add_column("Type", style="green")
    table.add_column("Episodes", style="yellow")
    table.add_column("Duration", style="blue")
    table.add_column("Score", style="magenta")

    for r in results:
        table.add_row(
            r.slug,
            r.title,
            r.anime_type or "N/A",
            r.episodes or "N/A",
            r.duration or "N/A",
            f"{r.score}/10" if r.score else "N/A",
        )
    console.print(table)


def print_series_detail(detail):
    if not detail:
        console.print("[red]Could not retrieve series details.[/red]")
        return

    info = f"""[bold cyan]Title:[/bold cyan] {detail.title}
[bold cyan]Slug:[/bold cyan] {detail.slug}
[bold cyan]AniList ID:[/bold cyan] {detail.anilist_id or 'N/A'} | [bold cyan]MAL ID:[/bold cyan] {detail.mal_id or 'N/A'}
[bold cyan]Status:[/bold cyan] {detail.status or 'N/A'} | [bold cyan]Score:[/bold cyan] {detail.average_score or 'N/A'}
[bold cyan]Season:[/bold cyan] {f"{detail.season} {detail.season_year}" if detail.season else 'N/A'}
[bold cyan]Genres:[/bold cyan] {', '.join(detail.genres) if detail.genres else 'N/A'}
[bold cyan]Total Episodes:[/bold cyan] {detail.total_episodes}
[bold cyan]Poster:[/bold cyan] {detail.poster or 'N/A'}
[bold cyan]Banner:[/bold cyan] {detail.banner or 'N/A'}
[bold cyan]Synopsis:[/bold cyan] {detail.synopsis[:250] + '...' if detail.synopsis else 'N/A'}
"""
    console.print(Panel(info, title=f"Series: {detail.title}", border_style="cyan"))

    if detail.episodes:
        table = Table(title=f"Episodes ({len(detail.episodes)})", header_style="bold cyan")
        table.add_column("Ep #", style="yellow")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Sub", style="green")
        table.add_column("Dub", style="magenta")
        table.add_column("Filler", style="red")
        table.add_column("Aired", style="blue")

        for ep in detail.episodes[:50]:
            table.add_row(
                str(ep.episode_num),
                ep.id,
                ep.title,
                "YES" if ep.is_subbed else "-",
                "YES" if ep.is_dubbed else "-",
                "YES" if ep.is_filler else "-",
                ep.aired_at or "N/A",
            )
        if len(detail.episodes) > 50:
            table.add_row("...", "...", f"and {len(detail.episodes) - 50} more episodes", "", "", "", "")
        console.print(table)


def print_stream_result(stream):
    if not stream:
        console.print("[red]Could not retrieve stream details.[/red]")
        return

    color = "green" if stream.status == "available" else "yellow"
    info = f"""[bold cyan]Slug:[/bold cyan] {stream.slug}
[bold cyan]Episode:[/bold cyan] {stream.episode_num}
[bold cyan]Status:[/bold cyan] [{color}]{stream.status}[/{color}]
[bold cyan]Embed URL:[/bold cyan] {stream.embed_url or 'None'}
[bold cyan]Message:[/bold cyan] {stream.message or 'N/A'}
"""
    console.print(Panel(info, title=f"ReAnime Stream - Ep {stream.episode_num}", border_style=color))


def print_stats(stats):
    table = Table(title="ReAnime Scraper Database Cache Stats", header_style="bold green")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold white")

    table.add_row("Total Series Cached", str(stats.total_series))
    table.add_row("Total Episodes Cached", str(stats.total_episodes))
    table.add_row("Total Streams Cached", str(stats.total_streams))
    table.add_row("Last Crawled", str(stats.last_crawled_at or "Never"))

    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="ReAnime (reanime.to) CLI Scraper")
    parser.add_argument("--search", "-s", nargs="?", const="", default=None, help="Search anime by title")
    parser.add_argument("--detail", "-d", type=str, help="Get full series metadata and episode roster by slug")
    parser.add_argument("--episode", "-e", type=str, help="Anime slug for stream extraction")
    parser.add_argument("--ep", type=int, default=1, help="Episode number (default: 1)")
    parser.add_argument("--stats", action="store_true", help="Show SQLite cache statistics")
    parser.add_argument("--no-cache", action="store_true", help="Bypass SQLite cache")
    parser.add_argument("--refresh", action="store_true", help="Bypass SQLite cache and fetch fresh data")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")

    args = parser.parse_args()
    scraper = ReAnimeScraper()
    use_cache = not (args.no_cache or args.refresh)

    try:
        if args.search is not None:
            results = scraper.search(args.search)
            if args.json:
                print(json.dumps([r.model_dump() for r in results], indent=2))
            else:
                print_search_results(results)
            if not results:
                sys.exit(1)

        elif args.detail:
            detail = scraper.get_series_detail(args.detail, use_cache=use_cache)
            if not detail:
                if args.json:
                    print(json.dumps({"error": "Anime not found"}, indent=2))
                else:
                    console.print("[red]Could not retrieve series details (Anime not found / 404).[/red]")
                sys.exit(1)

            if args.json:
                print(detail.model_dump_json(indent=2))
            else:
                print_series_detail(detail)

        elif args.episode:
            stream = scraper.get_episode_stream(args.episode, args.ep, use_cache=use_cache)
            if not stream:
                if args.json:
                    print(json.dumps({"error": "Stream not found"}, indent=2))
                else:
                    console.print(f"[red]Could not retrieve stream for episode {args.ep}.[/red]")
                sys.exit(1)

            if args.json:
                print(stream.model_dump_json(indent=2))
            else:
                print_stream_result(stream)

        elif args.stats:
            stats = scraper.storage.get_stats()
            if args.json:
                print(stats.model_dump_json(indent=2))
            else:
                print_stats(stats)

        else:
            parser.print_help()

    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
