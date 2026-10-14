"""
Rich interactive CLI for the Miruro Anime Scraper.
"""
import sys
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from .scraper import MiruroScraper

console = Console()


def cmd_search(args):
    scraper = MiruroScraper(cache_enabled=not args.no_cache)
    console.print(f"[bold cyan]Searching Miruro for:[/bold cyan] '{args.query}'...")
    try:
        results = scraper.search(args.query, limit=args.limit)
    except Exception as e:
        console.print(f"[red]Error searching Miruro: {e}[/red]")
        sys.exit(1)

    if not results:
        console.print("[yellow]No anime found matching your query.[/yellow]")
        sys.exit(1)

    table = Table(title=f"Miruro Search Results ({len(results)})", header_style="bold magenta")
    table.add_column("Miruro ID", style="dim")
    table.add_column("Title", style="white")
    table.add_column("Format", style="green")
    table.add_column("Episodes", style="cyan")
    table.add_column("Duration", style="blue")
    table.add_column("Score", style="yellow")
    table.add_column("Status", style="magenta")

    for r in results:
        table.add_row(
            r.id,
            r.title,
            r.format or "N/A",
            f"{r.episode_count} eps" if r.episode_count else "Ongoing",
            r.duration or "N/A",
            f"{int(r.average_score)}%" if r.average_score else "N/A",
            r.status or "N/A"
        )
    console.print(table)


def cmd_info(args):
    scraper = MiruroScraper(cache_enabled=not args.no_cache)
    console.print(f"[bold cyan]Fetching Miruro anime details for:[/bold cyan] {args.anime_id}...")
    try:
        series = scraper.get_series_detail(args.anime_id)
    except Exception as e:
        console.print(f"[red]Error fetching series details: {e}[/red]")
        sys.exit(1)

    if not series:
        console.print(f"[red]Series not found for ID: {args.anime_id}[/red]")
        sys.exit(1)

    title = series.title_english or series.title_romaji or "Unknown Title"
    info_text = (
        f"[bold white]Title (EN):[/bold white] {series.title_english or 'N/A'}\n"
        f"[bold white]Title (Romaji):[/bold white] {series.title_romaji or 'N/A'}\n"
        f"[bold white]Miruro ID:[/bold white] {series.id}\n"
        f"[bold white]Format:[/bold white] {series.format or 'N/A'}\n"
        f"[bold white]Status:[/bold white] {series.status or 'N/A'}\n"
        f"[bold white]Year / Season:[/bold white] {series.season_year or 'N/A'} ({series.season or 'N/A'})\n"
        f"[bold white]Score:[/bold white] {series.average_score}%\n"
        f"[bold white]Total Episodes:[/bold white] {len(series.episodes)}\n"
        f"[bold white]Genres:[/bold white] {', '.join(series.genres) if series.genres else 'None'}\n"
        f"[bold white]Studios:[/bold white] {', '.join(series.studios) if series.studios else 'None'}\n\n"
        f"[bold white]Synopsis:[/bold white]\n{(series.description or 'No synopsis available.').strip()[:400]}..."
    )
    console.print(Panel(info_text, title=f"[bold green]{title}[/bold green]", border_style="cyan"))

    if series.episodes:
        ep_table = Table(title=f"Episode Catalog (Total: {len(series.episodes)})", header_style="bold magenta")
        ep_table.add_column("Ep #", style="green", justify="right")
        ep_table.add_column("Episode ID", style="dim")
        ep_table.add_column("Title", style="white")
        ep_table.add_column("Duration", style="yellow")
        ep_table.add_column("Aired Date", style="dim")

        for ep in series.episodes[:30]:
            ep_num_str = f"{int(ep.episode_number)}" if ep.episode_number.is_integer() else f"{ep.episode_number}"
            dur_str = f"{ep.duration_minutes} min" if ep.duration_minutes else "N/A"
            ep_table.add_row(ep_num_str, ep.id, ep.title, dur_str, ep.aired_at or "N/A")

        console.print(ep_table)
        if len(series.episodes) > 30:
            console.print(f"[dim]... and {len(series.episodes) - 30} more episodes.[/dim]")


def cmd_episode(args):
    scraper = MiruroScraper(cache_enabled=not args.no_cache)
    console.print(f"[bold cyan]Fetching episode details for:[/bold cyan] {args.anime_id} (Episode {args.ep})...")
    try:
        ep = scraper.get_episode_detail(args.anime_id, float(args.ep))
    except Exception as e:
        console.print(f"[red]Error fetching episode details: {e}[/red]")
        sys.exit(1)

    if not ep:
        console.print(f"[red]Episode not found: {args.anime_id} (Episode {args.ep})[/red]")
        sys.exit(1)

    ep_num_str = f"{int(ep.episode_number)}" if ep.episode_number.is_integer() else f"{ep.episode_number}"
    panel_content = (
        f"[bold white]Title:[/bold white] {ep.title}\n"
        f"[bold white]Episode Number:[/bold white] {ep_num_str}\n"
        f"[bold white]Anime ID:[/bold white] {ep.anime_id}\n"
        f"[bold white]Subtitles Available:[/bold white] {len(ep.subtitles)} tracks\n"
        f"[bold white]Streaming Servers:[/bold white] {len(ep.servers)} mirrors\n"
        f"[bold white]Downloads Available:[/bold white] {len(ep.downloads)} files\n"
    )
    console.print(Panel(panel_content, title="[bold green]Episode Stream Details[/bold green]", border_style="blue"))

    if ep.servers:
        srv_table = Table(title=f"Decrypted Streaming Mirrors & Direct Streams ({len(ep.servers)})", header_style="bold magenta")
        srv_table.add_column("Server / Provider", style="white")
        srv_table.add_column("Track", style="green")
        srv_table.add_column("Format", style="cyan")
        srv_table.add_column("Quality", style="yellow")
        srv_table.add_column("Direct / Embed URL", style="dim")

        for s in ep.servers:
            srv_table.add_row(
                s.server_name,
                s.track_type.upper(),
                s.format.upper(),
                s.quality or "N/A",
                s.url or s.embed_url or "N/A"
            )
        console.print(srv_table)

    if ep.subtitles:
        sub_table = Table(title=f"Subtitle Tracks ({len(ep.subtitles)})", header_style="bold magenta")
        sub_table.add_column("Lang Code", style="green")
        sub_table.add_column("Label", style="white")
        sub_table.add_column("Format", style="yellow")
        sub_table.add_column("Subtitle URL", style="dim")

        for sub in ep.subtitles:
            sub_table.add_row(sub.language, sub.label, sub.format or "vtt", sub.file)
        console.print(sub_table)


def cmd_crawl(args):
    scraper = MiruroScraper(cache_enabled=not args.no_cache)
    console.print(f"[bold cyan]Starting crawl for Miruro anime:[/bold cyan] {args.anime_id}")
    series = scraper.crawl_series(args.anime_id, max_episodes=args.max_episodes)
    console.print(f"[green]SUCCESS: Crawl complete! Saved series and {len(series.episodes)} episodes into SQLite database.[/green]")


def cmd_stats(args):
    scraper = MiruroScraper()
    stats = scraper.storage.get_stats()
    content = (
        f"[bold white]Total Anime Series:[/bold white] {stats.total_series}\n"
        f"[bold white]Total Episodes Registered:[/bold white] {stats.total_episodes}\n"
        f"[bold green]Completed Episodes:[/bold green] {stats.completed_episodes}\n"
        f"[bold yellow]Pending Episodes:[/bold yellow] {stats.pending_episodes}\n"
        f"[bold red]Failed Episodes:[/bold red] {stats.failed_episodes}\n"
    )
    console.print(Panel(content, title="[bold magenta]Miruro SQLite Database Statistics[/bold magenta]", border_style="green"))


def cmd_export(args):
    scraper = MiruroScraper()
    out = scraper.storage.export_series_json(args.anime_id)
    if out:
        console.print(f"[green]✓ Successfully exported to {out}[/green]")
    else:
        console.print(f"[red]Error: Anime ID '{args.anime_id}' not found in database.[/red]")


def main():
    parser = argparse.ArgumentParser(description="Miruro Production Anime Scraper CLI")
    parser.add_argument("--search", dest="query", nargs="?", const="", default=None, help="Search anime by title keyword")
    parser.add_argument("--limit", type=int, default=15, help="Search result limit (default: 15)")
    parser.add_argument("--info", dest="anime_id", help="Miruro anime ID or URL")
    parser.add_argument("--episode", dest="ep_anime_id", help="Anime ID or URL for playback extraction")
    parser.add_argument("--ep", dest="ep_val", default="1", help="Episode number (default: 1)")
    parser.add_argument("--crawl", dest="crawl_anime_id", help="Crawl anime series and playback sources to SQLite")
    parser.add_argument("--max-episodes", type=int, default=None, help="Limit number of episodes to crawl")
    parser.add_argument("--stats", action="store_true", help="View database statistics")
    parser.add_argument("--export", dest="export_anime_id", help="Export anime and stream details to JSON")
    parser.add_argument("--no-cache", action="store_true", help="Bypass disk cache")

    args = parser.parse_args()

    try:
        if args.query is not None:
            if not args.query.strip():
                console.print("[yellow]No search query provided.[/yellow]")
                sys.exit(1)
            cmd_search(args)
        elif args.anime_id:
            cmd_info(args)
        elif args.ep_anime_id:
            args.anime_id = args.ep_anime_id
            args.ep = args.ep_val
            cmd_episode(args)
        elif args.crawl_anime_id:
            args.anime_id = args.crawl_anime_id
            cmd_crawl(args)
        elif args.stats:
            cmd_stats(args)
        elif args.export_anime_id:
            args.anime_id = args.export_anime_id
            cmd_export(args)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
