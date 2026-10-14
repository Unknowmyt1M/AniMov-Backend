"""Rich Command-Line Interface for WatchAnimeWorld Scraper."""

import argparse
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from .scraper import WatchAnimeWorldScraper
from .storage import WatchAnimeWorldStorage

console = Console()


def print_search_results(results):
    if not results:
        console.print("[yellow]No anime found matching your query.[/yellow]")
        return

    table = Table(title=f"WatchAnimeWorld Search Results ({len(results)})", header_style="bold magenta")
    table.add_column("Slug", style="cyan", no_wrap=False, overflow="fold")
    table.add_column("Title", style="bold white")
    table.add_column("Type", style="green")
    table.add_column("Episodes", style="yellow")
    table.add_column("Duration", style="blue")

    for r in results:
        table.add_row(
            r.slug,
            r.title,
            r.media_type,
            r.episodes or "N/A",
            r.duration or "N/A",
        )
    console.print(table)


def print_series_detail(detail):
    if not detail:
        console.print("[red]Could not retrieve series details.[/red]")
        return

    info = f"""[bold cyan]Title:[/bold cyan] {detail.title}
[bold cyan]Slug:[/bold cyan] {detail.slug}
[bold cyan]Genres:[/bold cyan] {', '.join(detail.genres) if detail.genres else 'N/A'}
[bold cyan]Total Episodes:[/bold cyan] {detail.total_episodes}
[bold cyan]Synopsis:[/bold cyan] {detail.synopsis[:200] + '...' if detail.synopsis else 'N/A'}
"""
    console.print(Panel(info, title=f"WatchAnimeWorld Series: {detail.title}", border_style="cyan"))

    if detail.episodes:
        table = Table(title=f"Episodes ({len(detail.episodes)})", header_style="bold cyan")
        table.add_column("Season", style="yellow")
        table.add_column("Ep #", style="yellow")
        table.add_column("Slug", style="cyan", no_wrap=False, overflow="fold")
        table.add_column("Title", style="white")

        for ep in detail.episodes[:25]:
            table.add_row(
                str(ep.season_num),
                str(ep.episode_num),
                ep.slug,
                ep.title,
            )
        if len(detail.episodes) > 25:
            table.add_row("...", "...", "...", f"(+ {len(detail.episodes) - 25} more)")
        console.print(table)


def print_episode_streams(ep):
    if not ep:
        console.print("[red]Could not retrieve episode streams.[/red]")
        return

    content = f"""[bold cyan]Episode:[/bold cyan] Season {ep.season_num}, Episode {ep.episode_num}
[bold cyan]Title:[/bold cyan] {ep.title}
"""
    if ep.servers:
        content += "\n[bold yellow]Available Servers / Embeds:[/bold yellow]\n"
        for s in ep.servers:
            content += f"  • [bold white]{s.name}:[/bold white] [underline cyan]{s.embed_url}[/underline cyan]\n"
    else:
        content += "\n[yellow]No parsed streaming servers found.[/yellow]\n"

    console.print(Panel(content, title=f"WatchAnimeWorld Episode: {ep.slug}", border_style="green"))


def main():
    parser = argparse.ArgumentParser(description="WatchAnimeWorld Scraper CLI")
    parser.add_argument("--search", "-s", type=str, nargs="?", const="", default=None, help="Search anime by title")
    parser.add_argument("--detail", "-d", type=str, help="Get series detail by slug or URL")
    parser.add_argument("--episode", "-e", type=str, help="Episode slug or URL (e.g. the-elusive-samurai-2x1)")
    parser.add_argument("--crawl", "-c", type=str, help="Crawl series and pre-cache episodes")
    parser.add_argument("--max-episodes", type=int, default=None, help="Limit number of episodes to crawl")
    parser.add_argument("--refresh", action="store_true", help="Bypass local cache and re-fetch from site")
    parser.add_argument("--stats", action="store_true", help="Display local SQLite cache stats")
    parser.add_argument("--export", type=str, help="Export cached series to JSON file")

    args = parser.parse_args()
    scraper = WatchAnimeWorldScraper()
    storage = WatchAnimeWorldStorage()

    try:
        if args.search is not None:
            results = scraper.search(args.search)
            print_search_results(results)
            if not results:
                sys.exit(1)

        elif args.detail:
            detail = scraper.get_series_detail(args.detail, use_cache=not args.refresh)
            if not detail:
                console.print("[red]Could not retrieve series details.[/red]")
                sys.exit(1)
            print_series_detail(detail)

        elif args.episode:
            ep = scraper.get_episode_streams(args.episode, use_cache=not args.refresh)
            if not ep:
                console.print("[red]Could not retrieve episode streams.[/red]")
                sys.exit(1)
            print_episode_streams(ep)

        elif args.crawl:
            detail = scraper.crawl_series(args.crawl, max_episodes=args.max_episodes)
            if not detail:
                sys.exit(1)
            print_series_detail(detail)

        elif args.stats:
            stats = storage.get_stats()
            console.print(
                Panel(
                    f"Total Series: {stats.total_series}\nTotal Episodes: {stats.total_episodes}\nTotal Streams: {stats.total_streams}\nLast Crawled: {stats.last_crawled_at or 'Never'}",
                    title="WatchAnimeWorld Local Storage Stats",
                    border_style="magenta",
                )
            )

        elif args.export:
            storage.export_json(Path(args.export))
            console.print(f"[green]Successfully exported data to {args.export}[/green]")

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
