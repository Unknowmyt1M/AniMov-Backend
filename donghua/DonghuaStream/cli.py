"""
Rich interactive CLI interface for DonghuaStream scraper.
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

from .scraper import DonghuaStreamScraper
from .sniffer import StreamSniffer

console = Console(safe_box=True)


def cmd_search(args):
    scraper = DonghuaStreamScraper(cache_enabled=not args.no_cache)
    console.print(f"[bold cyan]Searching DonghuaStream for:[/bold cyan] {args.query}...")
    results = scraper.search(args.query)

    if not results:
        console.print("[yellow]No series found matching query.[/yellow]")
        sys.exit(1)

    table = Table(title=f"Search Results for '{args.query}'", header_style="bold magenta")
    table.add_column("Title", style="cyan", no_wrap=False)
    table.add_column("Slug", style="green", no_wrap=False, overflow="fold")
    table.add_column("Type", style="yellow")
    table.add_column("Latest Ep", style="blue")
    table.add_column("URL", style="dim", no_wrap=False, overflow="fold")

    for r in results:
        table.add_row(r.title, r.slug, r.type_name or "ONA", r.latest_ep or "N/A", r.url)

    console.print(table)


def cmd_info(args):
    scraper = DonghuaStreamScraper(cache_enabled=not args.no_cache)
    console.print(f"[bold cyan]Fetching DonghuaStream series details for:[/bold cyan] {args.slug}...")
    series = scraper.get_series_detail(args.slug)

    if not series:
        console.print(f"[red]Could not retrieve series details for '{args.slug}'.[/red]")
        sys.exit(1)

    panel_content = (
        f"[bold white]Title:[/bold white] {series.title}\n"
        f"[bold white]Native Title:[/bold white] {series.native_title or 'N/A'}\n"
        f"[bold white]Status:[/bold white] {series.status or 'N/A'} | "
        f"[bold white]Rating:[/bold white] {series.rating or 'N/A'} | "
        f"[bold white]Type:[/bold white] {series.type_name or 'ONA'}\n"
        f"[bold white]Studio/Network:[/bold white] {series.studio or series.network or 'N/A'}\n"
        f"[bold white]Released:[/bold white] {series.released_date or 'N/A'} | "
        f"[bold white]Duration:[/bold white] {series.duration or 'N/A'}\n"
        f"[bold white]Genres:[/bold white] {', '.join(series.genres) if series.genres else 'N/A'}\n"
        f"[bold white]Poster:[/bold white] {series.poster or 'N/A'}\n\n"
        f"[bold white]Synopsis:[/bold white]\n{(series.synopsis[:300] + '...') if series.synopsis and len(series.synopsis) > 300 else (series.synopsis or 'N/A')}\n"
    )

    console.print(Panel(panel_content, title=f"[bold green]{series.title}[/bold green]", border_style="cyan"))

    if series.episodes:
        ep_table = Table(title=f"Discovered Episodes ({len(series.episodes)})", header_style="bold blue")
        ep_table.add_column("Ep #", style="green", width=6)
        ep_table.add_column("Title", style="white")
        ep_table.add_column("Release Date", style="dim")
        ep_table.add_column("URL", style="cyan")

        for ep in series.episodes[:30]:
            ep_num_str = f"{int(ep.episode_number)}" if ep.episode_number.is_integer() else f"{ep.episode_number}"
            ep_table.add_row(ep_num_str, ep.title, ep.release_date or "N/A", ep.url)

        console.print(ep_table)
        if len(series.episodes) > 30:
            console.print(f"[dim]... and {len(series.episodes) - 30} more episodes.[/dim]")


def cmd_episode(args):
    scraper = DonghuaStreamScraper(cache_enabled=not args.no_cache)
    console.print(f"[bold cyan]Fetching episode playback details from:[/bold cyan] {args.url}...")
    ep = scraper.get_episode_detail(args.url)

    ep_num_str = f"{int(ep.episode_number)}" if ep.episode_number.is_integer() else f"{ep.episode_number}"
    panel_content = (
        f"[bold white]Title:[/bold white] {ep.title}\n"
        f"[bold white]Episode Number:[/bold white] {ep_num_str}\n"
        f"[bold white]Release Date:[/bold white] {ep.release_date or 'N/A'}\n"
        f"[bold white]Parent Series:[/bold white] {ep.series_title or 'N/A'}\n"
        f"[bold white]Prev Episode:[/bold white] {ep.prev_episode or 'None'}\n"
        f"[bold white]Next Episode:[/bold white] {ep.next_episode or 'None'}\n"
    )
    console.print(Panel(panel_content, title="[bold green]Episode Info[/bold green]", border_style="blue"))

    if ep.servers:
        srv_table = Table(title=f"Streaming Server Mirrors ({len(ep.servers)})", header_style="bold magenta")
        srv_table.add_column("Server Name", style="white")
        srv_table.add_column("Provider", style="green")
        srv_table.add_column("Quality", style="yellow")
        srv_table.add_column("Languages", style="cyan")
        srv_table.add_column("Embed Iframe URL", style="dim")

        for s in ep.servers:
            srv_table.add_row(
                s.server_name,
                s.provider,
                s.quality or "Auto",
                ", ".join(s.languages) if s.languages else "Subtitled",
                s.embed_url
            )
        console.print(srv_table)

    if ep.downloads:
        dl_table = Table(title=f"Direct Download Links ({len(ep.downloads)})", header_style="bold green")
        dl_table.add_column("Title", style="white")
        dl_table.add_column("Host", style="yellow")
        dl_table.add_column("Quality", style="cyan")
        dl_table.add_column("URL", style="dim")

        for d in ep.downloads:
            dl_table.add_row(d.title, d.host or "Direct", d.quality or "Auto", d.url)
        console.print(dl_table)

    if args.sniff and ep.servers:
        first_embed = ep.servers[0].embed_url
        console.print(f"[bold yellow]Sniffing direct stream from:[/bold yellow] {first_embed}")
        sniff_res = StreamSniffer.sniff(first_embed)
        console.print(f"[bold green]Sniff Result:[/bold green] {sniff_res}")


def cmd_crawl(args):
    scraper = DonghuaStreamScraper(cache_enabled=not args.no_cache)
    console.print(f"[bold cyan]Starting crawl for DonghuaStream series:[/bold cyan] {args.slug}")
    series = scraper.crawl_series(args.slug, max_episodes=args.max_episodes)
    console.print(f"[green]✓ Crawl complete! Saved series and episodes to SQLite database.[/green]")


def cmd_stats(args):
    scraper = DonghuaStreamScraper()
    stats = scraper.storage.get_stats()
    content = (
        f"[bold white]Total Series:[/bold white] {stats.total_series}\n"
        f"[bold white]Total Episodes Registered:[/bold white] {stats.total_episodes}\n"
        f"[bold green]Completed Episodes:[/bold green] {stats.completed_episodes}\n"
        f"[bold yellow]Pending Episodes:[/bold yellow] {stats.pending_episodes}\n"
        f"[bold red]Failed Episodes:[/bold red] {stats.failed_episodes}\n"
    )
    console.print(Panel(content, title="[bold magenta]DonghuaStream SQLite Storage Statistics[/bold magenta]", border_style="green"))


def cmd_export(args):
    scraper = DonghuaStreamScraper()
    out = scraper.storage.export_series_json(args.slug)
    if out:
        console.print(f"[green]✓ Successfully exported to {out}[/green]")
    else:
        console.print(f"[red]Error: Series '{args.slug}' not found in database.[/red]")


def main():
    parser = argparse.ArgumentParser(description="DonghuaStream Production Scraper CLI")
    parser.add_argument("--search", dest="query", nargs="?", const="", default=None, help="Search donghua series by keyword")
    parser.add_argument("--info", dest="slug", help="Fetch series details by slug or URL")
    parser.add_argument("--episode", dest="url", help="Fetch episode stream mirrors and download options")
    parser.add_argument("--sniff", action="store_true", help="Sniff direct m3u8/mp4 using Playwright")
    parser.add_argument("--crawl", dest="crawl_slug", help="Crawl all episodes of a series into SQLite")
    parser.add_argument("--max-episodes", type=int, default=None, help="Limit number of episodes to crawl")
    parser.add_argument("--stats", action="store_true", help="View database statistics")
    parser.add_argument("--export", dest="export_slug", help="Export series data to JSON")
    parser.add_argument("--no-cache", action="store_true", help="Bypass disk cache")

    args = parser.parse_args()

    try:
        if args.query is not None:
            if not args.query.strip():
                console.print("[yellow]No search query provided.[/yellow]")
                sys.exit(1)
            cmd_search(args)
        elif args.slug:
            cmd_info(args)
        elif args.url:
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
