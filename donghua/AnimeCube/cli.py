"""
Rich interactive CLI interface for AnimeCube scraper.
"""
import sys
import argparse
from rich.panel import Panel

from common.ui import (
    console,
    print_banner,
    status_spinner,
    create_table,
    box,
)

try:
    from .scraper import AnimeCubeScraper
    from .sniffer import StreamSniffer
except ImportError:
    from donghua.AnimeCube.scraper import AnimeCubeScraper
    from donghua.AnimeCube.sniffer import StreamSniffer


def cmd_catalog(args):
    scraper = AnimeCubeScraper(cache_enabled=not args.no_cache)
    with status_spinner("Fetching full AnimeCube catalog..."):
        items = scraper.list_catalog()

    table = create_table(
        title=f"✨ AnimeCube Catalog ({len(items)} Series) ✨",
        columns=[
            ("Title", {"style": "bold bright_white"}),
            ("Slug", {"style": "bright_green"}),
            ("URL", {"style": "underline cyan"}),
        ],
        border_style="bright_blue",
        header_style="bold bright_magenta",
    )

    for item in items:
        table.add_row(item.title, item.slug, item.url)

    console.print(table)


def cmd_search(args):
    scraper = AnimeCubeScraper(cache_enabled=not args.no_cache)
    with status_spinner(f"Searching AnimeCube for '{args.query}'..."):
        results = scraper.search(args.query)

    if not results:
        console.print("\n[yellow]⚠️  No series found matching query.[/yellow]\n")
        sys.exit(1)

    table = create_table(
        title=f"✨ Search Results for '{args.query}' ({len(results)}) ✨",
        columns=[
            ("Title", {"style": "bold bright_white"}),
            ("Slug", {"style": "bright_green"}),
            ("URL", {"style": "underline cyan"}),
        ],
        border_style="bright_blue",
        header_style="bold bright_magenta",
    )

    for r in results:
        table.add_row(r.title, r.slug, r.url)

    console.print(table)


def cmd_info(args):
    scraper = AnimeCubeScraper(cache_enabled=not args.no_cache)
    with status_spinner(f"Fetching AnimeCube series details for '{args.slug}'..."):
        try:
            series = scraper.get_series_detail(args.slug)
        except Exception as e:
            console.print(f"[red]❌ Error fetching series details: {e}[/red]")
            sys.exit(1)

    if not series:
        console.print(f"[red]❌ Series not found: {args.slug}[/red]")
        sys.exit(1)

    genres_str = " • ".join(f"[bold bright_magenta]{g}[/]" for g in series.genres) if series.genres else "[dim]N/A[/dim]"
    tags_str = ", ".join(series.tags) if series.tags else "[dim]N/A[/dim]"
    schedule_str = f"{', '.join(series.update_days) if series.update_days else 'N/A'} {series.update_time or ''}".strip()

    panel_content = f"""[bold bright_white]🎬 Title:[/bold bright_white]         [bold bright_yellow]{series.title}[/bold bright_yellow]
[bold bright_white]🔖 Slug:[/bold bright_white]          [cyan]{series.slug}[/cyan]
[bold bright_white]📡 Status:[/bold bright_white]        [bright_blue]{series.status or 'N/A'}[/bright_blue]
[bold bright_white]📅 Year:[/bold bright_white]          [bright_green]{series.year or 'N/A'}[/bright_green]
[bold bright_white]🎞️  Total Episodes:[/bold bright_white] [bold bright_cyan]{series.total_episodes or len(series.episodes)}[/bold bright_cyan]
[bold bright_white]⏰ Schedule:[/bold bright_white]      [bright_yellow]{schedule_str}[/bright_yellow]
[bold bright_white]🎭 Genres:[/bold bright_white]        {genres_str}
[bold bright_white]🏷️  Tags:[/bold bright_white]          [dim]{tags_str}[/dim]

[bold bright_white]📖 Synopsis:[/bold bright_white]
[italic white]{series.synopsis.strip() if series.synopsis else 'N/A'}[/italic white]
"""
    console.print(
        Panel(
            panel_content.strip(),
            title=f"[bold bright_cyan]✦ {series.title.upper()} ✦[/bold bright_cyan]",
            border_style="bright_cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    if series.episodes:
        show_all = getattr(args, "all", False)
        ep_limit = 50 if not show_all else len(series.episodes)
        ep_list = series.episodes if show_all else series.episodes[:ep_limit]

        ep_table = create_table(
            title=f"📺 Discovered Episodes ({len(series.episodes)} Total{' - Showing First ' + str(ep_limit) if not show_all and len(series.episodes) > ep_limit else ''})",
            columns=[
                ("Ep #", {"style": "bold bright_yellow", "justify": "center", "width": 8}),
                ("Episode ID", {"style": "cyan"}),
                ("Title", {"style": "bold bright_white"}),
                ("Duration", {"style": "bright_blue", "justify": "center"}),
                ("Published Date", {"style": "dim white", "justify": "center"}),
            ],
            border_style="cyan",
            header_style="bold bright_cyan",
        )

        for ep in ep_list:
            ep_num_str = f"{int(ep.episode_number)}" if ep.episode_number.is_integer() else f"{ep.episode_number}"
            duration_str = f"{ep.duration} min" if ep.duration else "N/A"
            ep_table.add_row(
                ep_num_str,
                ep.id,
                ep.title or f"Episode {ep_num_str}",
                duration_str,
                ep.published_at or "N/A",
            )

        if not show_all and len(series.episodes) > ep_limit:
            remaining = len(series.episodes) - ep_limit
            ep_table.add_row("...", "...", f"[dim italic]+ {remaining} more episodes (use --all to show all)[/dim italic]", "...", "...")

        console.print(ep_table)


def cmd_episode(args):
    scraper = AnimeCubeScraper(cache_enabled=not args.no_cache)
    with status_spinner(f"Fetching episode details for '{args.slug}' (Ep {args.ep})..."):
        try:
            ep = scraper.get_episode_detail(args.slug, args.ep)
        except Exception as e:
            console.print(f"[red]❌ Error fetching episode details: {e}[/red]")
            sys.exit(1)

    if not ep:
        console.print(f"[red]❌ Episode not found: {args.slug} (Episode: {args.ep})[/red]")
        sys.exit(1)

    ep_num_str = f"{int(ep.episode_number)}" if ep.episode_number.is_integer() else f"{ep.episode_number}"
    panel_content = f"""[bold bright_white]🎬 Title:[/bold bright_white]          [bold bright_yellow]{ep.title}[/bold bright_yellow]
[bold bright_white]🔖 Episode ID:[/bold bright_white]     [cyan]{ep.id}[/cyan]
[bold bright_white]🔢 Episode Number:[/bold bright_white] [bold bright_cyan]{ep_num_str}[/bold bright_cyan]
[bold bright_white]⏱️  Duration:[/bold bright_white]       [bright_green]{ep.duration or 'N/A'} min[/bright_green]
[bold bright_white]📅 Published:[/bold bright_white]      [dim]{ep.published_at or 'N/A'}[/dim]
[bold bright_white]📚 Series:[/bold bright_white]         [white]{ep.series_title or ep.series_slug}[/white]
[bold bright_white]🔗 Watch URL:[/bold bright_white]      [underline cyan]{ep.url}[/underline cyan]
"""
    console.print(
        Panel(
            panel_content.strip(),
            title=f"[bold bright_green]✦ Episode Playback Info: Episode {ep_num_str} ✦[/bold bright_green]",
            border_style="bright_green",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    if ep.servers:
        srv_table = create_table(
            title=f"🖥️  Decrypted Streaming Servers & Video Sources ({len(ep.servers)})",
            columns=[
                ("Server Name", {"style": "bold bright_white"}),
                ("Platform", {"style": "bright_green", "justify": "center"}),
                ("Video ID", {"style": "cyan"}),
                ("Quality", {"style": "bright_yellow", "justify": "center"}),
                ("Embed / Player URL", {"style": "underline cyan"}),
            ],
            border_style="bright_green",
            header_style="bold bright_green",
        )

        for s in ep.servers:
            srv_table.add_row(
                s.server_name,
                s.platform or s.provider or "N/A",
                s.video_id or "N/A",
                s.quality or "Auto",
                s.embed_url,
            )
        console.print(srv_table)

    if getattr(args, "sniff", False) and ep.servers:
        first_embed = ep.servers[0].embed_url
        with status_spinner(f"Sniffing direct stream from '{first_embed}'..."):
            sniff_res = StreamSniffer.sniff(first_embed)
        console.print(f"[bold bright_green]✓ Sniff Result:[/bold bright_green] {sniff_res}")


def cmd_crawl(args):
    scraper = AnimeCubeScraper(cache_enabled=not args.no_cache)
    with status_spinner(f"Crawling AnimeCube series '{args.slug}'..."):
        series = scraper.crawl_series(args.slug, max_episodes=args.max_episodes)
    console.print(f"[bold bright_green]✓ Crawl complete! Saved series and {len(series.episodes)} episodes to SQLite database.[/bold bright_green]")


def cmd_stats(args):
    scraper = AnimeCubeScraper()
    stats = scraper.storage.get_stats()
    content = f"""[bold bright_white]📚 Total Series:[/bold bright_white]             [bold cyan]{stats.total_series}[/bold cyan]
[bold bright_white]📺 Total Episodes Registered:[/bold bright_white] [bold yellow]{stats.total_episodes}[/bold yellow]
[bold bright_white]✓ Completed Episodes:[/bold bright_white]         [bold green]{stats.completed_episodes}[/bold green]
[bold bright_white]⏳ Pending Episodes:[/bold bright_white]           [bright_yellow]{stats.pending_episodes}[/bright_yellow]
[bold bright_white]❌ Failed Episodes:[/bold bright_white]            [bold red]{stats.failed_episodes}[/bold red]
"""
    console.print(
        Panel(
            content.strip(),
            title="[bold bright_magenta]✦ AnimeCube SQLite Storage Statistics ✦[/bold bright_magenta]",
            border_style="bright_magenta",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def cmd_export(args):
    scraper = AnimeCubeScraper()
    with status_spinner(f"Exporting series '{args.slug}' to JSON..."):
        out = scraper.storage.export_series_json(args.slug)
    if out:
        console.print(f"[green]✓ Successfully exported to {out}[/green]")
    else:
        console.print(f"[red]❌ Error: Series '{args.slug}' not found in database.[/red]")


def main():
    parser = argparse.ArgumentParser(description="AnimeCube Next.js Production Scraper CLI")
    parser.add_argument("--catalog", action="store_true", help="List all series available on AnimeCube")
    parser.add_argument("--search", dest="query", nargs="?", const="", default=None, help="Search series by keyword")
    parser.add_argument("--info", dest="slug", help="Fetch series details and episode list by slug")
    parser.add_argument("--all", "-a", action="store_true", help="Show all episodes without truncating")
    parser.add_argument("--episode", dest="ep_slug", help="Series slug for episode playback info")
    parser.add_argument("--ep", dest="ep_val", default="1", help="Episode ID or number (default: 1)")
    parser.add_argument("--sniff", action="store_true", help="Sniff direct m3u8/mp4 using Playwright")
    parser.add_argument("--crawl", dest="crawl_slug", help="Crawl series episodes into SQLite database")
    parser.add_argument("--max-episodes", type=int, default=None, help="Limit number of episodes to crawl")
    parser.add_argument("--stats", action="store_true", help="View database statistics")
    parser.add_argument("--export", dest="export_slug", help="Export series data to JSON")
    parser.add_argument("--no-cache", action="store_true", help="Bypass disk cache")

    args = parser.parse_args()

    print_banner("AnimeCube", "Donghua Streaming & Server Decryptor")

    try:
        if args.catalog:
            cmd_catalog(args)
        elif args.query is not None:
            if not args.query.strip():
                console.print("[yellow]⚠️  No search query provided.[/yellow]")
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
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
