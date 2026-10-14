"""
Rich interactive CLI interface for AnimeCube scraper.
"""
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .scraper import AnimeCubeScraper
from .sniffer import StreamSniffer

console = Console(safe_box=True)


def cmd_catalog(args):
    scraper = AnimeCubeScraper(cache_enabled=not args.no_cache)
    console.print("[bold cyan]Fetching full AnimeCube catalog...[/bold cyan]")
    items = scraper.list_catalog()

    table = Table(title=f"AnimeCube Catalog ({len(items)} Series)", header_style="bold magenta")
    table.add_column("Title", style="cyan", no_wrap=False)
    table.add_column("Slug", style="green")
    table.add_column("URL", style="dim")

    for item in items:
        table.add_row(item.title, item.slug, item.url)

    console.print(table)


def cmd_search(args):
    scraper = AnimeCubeScraper(cache_enabled=not args.no_cache)
    console.print(f"[bold cyan]Searching AnimeCube for:[/bold cyan] {args.query}...")
    results = scraper.search(args.query)

    if not results:
        console.print("[yellow]No series found matching query.[/yellow]")
        sys.exit(1)

    table = Table(title=f"Search Results for '{args.query}'", header_style="bold magenta")
    table.add_column("Title", style="cyan", no_wrap=False)
    table.add_column("Slug", style="green")
    table.add_column("URL", style="dim")

    for r in results:
        table.add_row(r.title, r.slug, r.url)

    console.print(table)


def cmd_info(args):
    scraper = AnimeCubeScraper(cache_enabled=not args.no_cache)
    console.print(f"[bold cyan]Fetching AnimeCube series details for:[/bold cyan] {args.slug}...")
    try:
        series = scraper.get_series_detail(args.slug)
    except Exception as e:
        console.print(f"[red]Error fetching series details: {e}[/red]")
        sys.exit(1)

    if not series:
        console.print(f"[red]Series not found: {args.slug}[/red]")
        sys.exit(1)

    panel_content = (
        f"[bold white]Title:[/bold white] {series.title}\n"
        f"[bold white]Status:[/bold white] {series.status or 'N/A'} | "
        f"[bold white]Year:[/bold white] {series.year or 'N/A'} | "
        f"[bold white]Total Episodes:[/bold white] {series.total_episodes or len(series.episodes)}\n"
        f"[bold white]Genres:[/bold white] {', '.join(series.genres) if series.genres else 'N/A'}\n"
        f"[bold white]Tags:[/bold white] {', '.join(series.tags) if series.tags else 'N/A'}\n"
        f"[bold white]Schedule:[/bold white] {', '.join(series.update_days) if series.update_days else 'N/A'} {series.update_time or ''}\n"
        f"[bold white]Cover:[/bold white] {series.cover_image or 'N/A'}\n\n"
        f"[bold white]Synopsis:[/bold white]\n{(series.synopsis[:300] + '...') if series.synopsis and len(series.synopsis) > 300 else (series.synopsis or 'N/A')}\n"
    )

    console.print(Panel(panel_content, title=f"[bold green]{series.title}[/bold green]", border_style="cyan"))

    if series.episodes:
        ep_table = Table(title=f"Discovered Episodes ({len(series.episodes)})", header_style="bold blue")
        ep_table.add_column("Ep #", style="green", width=6)
        ep_table.add_column("Episode ID", style="dim")
        ep_table.add_column("Title", style="white")
        ep_table.add_column("Duration", style="yellow")
        ep_table.add_column("Published Date", style="dim")

        for ep in series.episodes[:30]:
            ep_num_str = f"{int(ep.episode_number)}" if ep.episode_number.is_integer() else f"{ep.episode_number}"
            duration_str = f"{ep.duration} min" if ep.duration else "N/A"
            ep_table.add_row(ep_num_str, ep.id, ep.title, duration_str, ep.published_at or "N/A")

        console.print(ep_table)
        if len(series.episodes) > 30:
            console.print(f"[dim]... and {len(series.episodes) - 30} more episodes.[/dim]")


def cmd_episode(args):
    scraper = AnimeCubeScraper(cache_enabled=not args.no_cache)
    console.print(f"[bold cyan]Fetching episode details for:[/bold cyan] {args.slug} (Episode: {args.ep})...")
    try:
        ep = scraper.get_episode_detail(args.slug, args.ep)
    except Exception as e:
        console.print(f"[red]Error fetching episode details: {e}[/red]")
        sys.exit(1)

    if not ep:
        console.print(f"[red]Episode not found: {args.slug} (Episode: {args.ep})[/red]")
        sys.exit(1)

    ep_num_str = f"{int(ep.episode_number)}" if ep.episode_number.is_integer() else f"{ep.episode_number}"
    panel_content = (
        f"[bold white]Title:[/bold white] {ep.title}\n"
        f"[bold white]Episode ID:[/bold white] {ep.id}\n"
        f"[bold white]Episode Number:[/bold white] {ep_num_str}\n"
        f"[bold white]Duration:[/bold white] {ep.duration or 'N/A'} min\n"
        f"[bold white]Published Date:[/bold white] {ep.published_at or 'N/A'}\n"
        f"[bold white]Series:[/bold white] {ep.series_title or ep.series_slug}\n"
        f"[bold white]Watch URL:[/bold white] {ep.url}\n"
        f"[bold white]Prev Episode:[/bold white] {ep.prev_episode or 'None'}\n"
        f"[bold white]Next Episode:[/bold white] {ep.next_episode or 'None'}\n"
    )
    console.print(Panel(panel_content, title="[bold green]Episode Playback Info[/bold green]", border_style="blue"))

    if ep.servers:
        srv_table = Table(title=f"Decrypted Streaming Servers & Video Sources ({len(ep.servers)})", header_style="bold magenta")
        srv_table.add_column("Server Name", style="white")
        srv_table.add_column("Platform", style="green")
        srv_table.add_column("Video ID", style="cyan")
        srv_table.add_column("Quality", style="yellow")
        srv_table.add_column("Embed / Player URL", style="dim")

        for s in ep.servers:
            srv_table.add_row(
                s.server_name,
                s.platform or s.provider,
                s.video_id or "N/A",
                s.quality or "Auto",
                s.embed_url
            )
        console.print(srv_table)

    if args.sniff and ep.servers:
        first_embed = ep.servers[0].embed_url
        console.print(f"[bold yellow]Sniffing direct stream from:[/bold yellow] {first_embed}")
        sniff_res = StreamSniffer.sniff(first_embed)
        console.print(f"[bold green]Sniff Result:[/bold green] {sniff_res}")


def cmd_crawl(args):
    scraper = AnimeCubeScraper(cache_enabled=not args.no_cache)
    console.print(f"[bold cyan]Starting crawl for AnimeCube series:[/bold cyan] {args.slug}")
    series = scraper.crawl_series(args.slug, max_episodes=args.max_episodes)
    console.print(f"[green]✓ Crawl complete! Saved series and {len(series.episodes)} episodes to SQLite database.[/green]")


def cmd_stats(args):
    scraper = AnimeCubeScraper()
    stats = scraper.storage.get_stats()
    content = (
        f"[bold white]Total Series:[/bold white] {stats.total_series}\n"
        f"[bold white]Total Episodes Registered:[/bold white] {stats.total_episodes}\n"
        f"[bold green]Completed Episodes:[/bold green] {stats.completed_episodes}\n"
        f"[bold yellow]Pending Episodes:[/bold yellow] {stats.pending_episodes}\n"
        f"[bold red]Failed Episodes:[/bold red] {stats.failed_episodes}\n"
    )
    console.print(Panel(content, title="[bold magenta]AnimeCube SQLite Storage Statistics[/bold magenta]", border_style="green"))


def cmd_export(args):
    scraper = AnimeCubeScraper()
    out = scraper.storage.export_series_json(args.slug)
    if out:
        console.print(f"[green]✓ Successfully exported to {out}[/green]")
    else:
        console.print(f"[red]Error: Series '{args.slug}' not found in database.[/red]")


def main():
    parser = argparse.ArgumentParser(description="AnimeCube Next.js Production Scraper CLI")
    parser.add_argument("--catalog", action="store_true", help="List all series available on AnimeCube")
    parser.add_argument("--search", dest="query", nargs="?", const="", default=None, help="Search series by keyword")
    parser.add_argument("--info", dest="slug", help="Fetch series details and episode list by slug")
    parser.add_argument("--episode", dest="ep_slug", help="Series slug for episode playback info")
    parser.add_argument("--ep", dest="ep_val", default="1", help="Episode ID or number (default: 1)")
    parser.add_argument("--sniff", action="store_true", help="Sniff direct m3u8/mp4 using Playwright")
    parser.add_argument("--crawl", dest="crawl_slug", help="Crawl series episodes into SQLite database")
    parser.add_argument("--max-episodes", type=int, default=None, help="Limit number of episodes to crawl")
    parser.add_argument("--stats", action="store_true", help="View database statistics")
    parser.add_argument("--export", dest="export_slug", help="Export series data to JSON")
    parser.add_argument("--no-cache", action="store_true", help="Bypass disk cache")

    args = parser.parse_args()

    try:
        if args.catalog:
            cmd_catalog(args)
        elif args.query is not None:
            if not args.query.strip():
                console.print("[yellow]No search query provided.[/yellow]")
                sys.exit(1)
            cmd_search(args)
        elif args.slug:
            cmd_info(args)
        elif args.ep_slug:
            args.slug = args.ep_slug
            args.ep = args.ep_val
            cmd_episode(args)
        elif args.crawl_slug:
            args.slug = args.crawl_slug
            cmd_crawl(args)
        elif args.stats:
            cmd_stats(args)
        elif args.export_slug:
            args.slug = args.export_slug
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
