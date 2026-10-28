"""
Rich interactive CLI interface for AnimeKhor scraper.
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
    from .scraper import AnimeKhorScraper
    from .sniffer import StreamSniffer
except ImportError:
    from donghua.AnimeKhor.scraper import AnimeKhorScraper
    from donghua.AnimeKhor.sniffer import StreamSniffer


def cmd_search(args):
    scraper = AnimeKhorScraper(cache_enabled=not args.no_cache)
    with status_spinner(f"Searching AnimeKhor for '{args.query}'..."):
        results = scraper.search(args.query)

    if not results:
        console.print("\n[yellow]⚠️  No series found matching query.[/yellow]\n")
        sys.exit(1)

    table = create_table(
        title=f"✨ Search Results for '{args.query}' ({len(results)}) ✨",
        columns=[
            ("Title", {"style": "bold bright_white"}),
            ("Slug", {"style": "bright_green"}),
            ("Type", {"style": "bright_yellow", "justify": "center"}),
            ("Latest Ep", {"style": "bright_blue", "justify": "center"}),
            ("URL", {"style": "underline cyan"}),
        ],
        border_style="bright_blue",
        header_style="bold bright_magenta",
    )

    for r in results:
        type_badge = f"[bold on dark_blue] {r.type_name or 'ONA'} [/]"
        table.add_row(r.title, r.slug, type_badge, r.latest_ep or "N/A", r.url)

    console.print(table)


def cmd_info(args):
    scraper = AnimeKhorScraper(cache_enabled=not args.no_cache)
    with status_spinner(f"Fetching AnimeKhor series details for '{args.slug}'..."):
        try:
            series = scraper.get_series_detail(args.slug)
        except Exception as e:
            console.print(f"[red]❌ Could not retrieve series details for '{args.slug}': {e}[/red]")
            sys.exit(1)

    if not series:
        console.print(f"[red]❌ Series not found: {args.slug}[/red]")
        sys.exit(1)

    genres_str = " • ".join(f"[bold bright_magenta]{g}[/]" for g in series.genres) if series.genres else "[dim]N/A[/dim]"
    rating_str = f"⭐ [bold bright_yellow]{series.rating}[/bold bright_yellow]" if series.rating else "[dim]N/A[/dim]"

    panel_content = f"""[bold bright_white]🎬 Title:[/bold bright_white]        [bold bright_yellow]{series.title}[/bold bright_yellow]
[bold bright_white]🇨🇳 Native Title:[/bold bright_white] [white]{series.native_title or 'N/A'}[/white]
[bold bright_white]📡 Status:[/bold bright_white]       [bright_blue]{series.status or 'N/A'}[/bright_blue]
[bold bright_white]⭐ Rating:[/bold bright_white]       {rating_str}
[bold bright_white]📺 Type:[/bold bright_white]         [bold on dark_blue] {series.type_name or 'ONA'} [/]
[bold bright_white]🏢 Studio:[/bold bright_white]       [bright_green]{series.studio or 'N/A'}[/bright_green]
[bold bright_white]🌏 Country:[/bold bright_white]      [dim]{series.country or 'China'}[/dim]
[bold bright_white]📅 Released:[/bold bright_white]     [bright_cyan]{series.released_date or 'N/A'}[/bright_cyan]
[bold bright_white]⏱️  Duration:[/bold bright_white]     [bright_yellow]{series.duration or 'N/A'}[/bright_yellow]
[bold bright_white]🎭 Genres:[/bold bright_white]       {genres_str}

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
                ("Title", {"style": "bold bright_white"}),
                ("Release Date", {"style": "dim white", "justify": "center"}),
                ("URL", {"style": "underline cyan"}),
            ],
            border_style="cyan",
            header_style="bold bright_cyan",
        )

        for ep in ep_list:
            ep_num_str = f"{int(ep.episode_number)}" if ep.episode_number.is_integer() else f"{ep.episode_number}"
            ep_table.add_row(
                ep_num_str,
                ep.title or f"Episode {ep_num_str}",
                ep.release_date or "N/A",
                ep.url,
            )

        if not show_all and len(series.episodes) > ep_limit:
            remaining = len(series.episodes) - ep_limit
            ep_table.add_row("...", f"[dim italic]+ {remaining} more episodes (use --all to show all)[/dim italic]", "...", "...")

        console.print(ep_table)


def cmd_episode(args):
    scraper = AnimeKhorScraper(cache_enabled=not args.no_cache)
    with status_spinner(f"Fetching episode playback details from '{args.url}'..."):
        try:
            ep = scraper.get_episode_detail(args.url)
        except Exception as e:
            console.print(f"[red]❌ Could not retrieve episode playback details: {e}[/red]")
            sys.exit(1)

    if not ep:
        console.print(f"[red]❌ Episode not found: {args.url}[/red]")
        sys.exit(1)

    ep_num_str = f"{int(ep.episode_number)}" if ep.episode_number.is_integer() else f"{ep.episode_number}"
    panel_content = f"""[bold bright_white]🎬 Title:[/bold bright_white]          [bold bright_yellow]{ep.title}[/bold bright_yellow]
[bold bright_white]🔢 Episode Number:[/bold bright_white] [bold bright_cyan]{ep_num_str}[/bold bright_cyan]
[bold bright_white]📅 Release Date:[/bold bright_white]   [dim]{ep.release_date or 'N/A'}[/dim]
[bold bright_white]📚 Parent Series:[/bold bright_white]  [white]{ep.series_title or 'N/A'}[/white]
[bold bright_white]⏪ Prev Episode:[/bold bright_white]   [dim]{ep.prev_episode or 'None'}[/dim]
[bold bright_white]⏩ Next Episode:[/bold bright_white]   [dim]{ep.next_episode or 'None'}[/dim]
"""
    console.print(
        Panel(
            panel_content.strip(),
            title=f"[bold bright_green]✦ Episode Playback: Episode {ep_num_str} ✦[/bold bright_green]",
            border_style="bright_green",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    if ep.servers:
        srv_table = create_table(
            title=f"🖥️  Streaming Server Mirrors ({len(ep.servers)})",
            columns=[
                ("Server Name", {"style": "bold bright_white"}),
                ("Provider", {"style": "bright_green", "justify": "center"}),
                ("Quality", {"style": "bright_yellow", "justify": "center"}),
                ("Languages", {"style": "bright_cyan", "justify": "center"}),
                ("Embed Iframe URL", {"style": "underline cyan"}),
            ],
            border_style="bright_green",
            header_style="bold bright_green",
        )

        for s in ep.servers:
            srv_table.add_row(
                s.server_name,
                s.provider,
                s.quality or "Auto",
                ", ".join(s.languages) if s.languages else "Subtitled",
                s.embed_url,
            )
        console.print(srv_table)

    if ep.downloads:
        dl_table = create_table(
            title=f"⬇️  Direct Download Links ({len(ep.downloads)})",
            columns=[
                ("Title", {"style": "bold bright_white"}),
                ("Host", {"style": "bright_yellow", "justify": "center"}),
                ("Quality", {"style": "bright_cyan", "justify": "center"}),
                ("Download URL", {"style": "underline dim"}),
            ],
            border_style="bright_yellow",
            header_style="bold bright_yellow",
        )

        for d in ep.downloads:
            dl_table.add_row(d.title, d.host or "Direct", d.quality or "Auto", d.url)
        console.print(dl_table)

    if getattr(args, "sniff", False) and ep.servers:
        first_embed = ep.servers[0].embed_url
        with status_spinner(f"Sniffing direct stream from '{first_embed}'..."):
            sniff_res = StreamSniffer.sniff(first_embed)
        console.print(f"[bold bright_green]✓ Sniff Result:[/bold bright_green] {sniff_res}")


def cmd_crawl(args):
    scraper = AnimeKhorScraper(cache_enabled=not args.no_cache)
    with status_spinner(f"Crawling AnimeKhor series '{args.slug}'..."):
        scraper.crawl_series(args.slug, max_episodes=args.max_episodes)
    console.print(f"[bold bright_green]✓ Crawl complete! Saved series and episodes to SQLite database.[/bold bright_green]")


def cmd_stats(args):
    scraper = AnimeKhorScraper()
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
            title="[bold bright_magenta]✦ AnimeKhor SQLite Storage Statistics ✦[/bold bright_magenta]",
            border_style="bright_magenta",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def cmd_export(args):
    scraper = AnimeKhorScraper()
    with status_spinner(f"Exporting series '{args.slug}' to JSON..."):
        out = scraper.storage.export_series_json(args.slug)
    if out:
        console.print(f"[green]✓ Successfully exported to {out}[/green]")
    else:
        console.print(f"[red]❌ Error: Series '{args.slug}' not found in database.[/red]")


def main():
    parser = argparse.ArgumentParser(description="AnimeKhor Production Scraper CLI")
    parser.add_argument("--search", dest="query", nargs="?", const="", default=None, help="Search anime/donghua series by keyword")
    parser.add_argument("--info", dest="slug", help="Fetch series details by slug or URL")
    parser.add_argument("--all", "-a", action="store_true", help="Show all episodes without truncating")
    parser.add_argument("--episode", dest="url", help="Fetch episode stream mirrors and download options")
    parser.add_argument("--sniff", action="store_true", help="Sniff direct m3u8/mp4 using Playwright")
    parser.add_argument("--crawl", dest="crawl_slug", help="Crawl all episodes of a series into SQLite")
    parser.add_argument("--max-episodes", type=int, default=None, help="Limit number of episodes to crawl")
    parser.add_argument("--stats", action="store_true", help="View database statistics")
    parser.add_argument("--export", dest="export_slug", help="Export series data to JSON")
    parser.add_argument("--no-cache", action="store_true", help="Bypass disk cache")

    args = parser.parse_args()

    print_banner("AnimeKhor", "High Quality Donghua & Anime Scraper")

    try:
        if args.query is not None:
            if not args.query.strip():
                console.print("[yellow]⚠️  No search query provided.[/yellow]")
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
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
