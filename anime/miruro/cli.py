"""
Rich interactive CLI for the Miruro Anime Scraper.
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
    from .scraper import MiruroScraper
except ImportError:
    from anime.miruro.scraper import MiruroScraper


def cmd_search(args):
    scraper = MiruroScraper(cache_enabled=not args.no_cache)
    with status_spinner(f"Searching Miruro for '{args.query}'..."):
        try:
            results = scraper.search(args.query, limit=args.limit)
        except Exception as e:
            console.print(f"[red]❌ Error searching Miruro: {e}[/red]")
            sys.exit(1)

    if not results:
        console.print("\n[yellow]⚠️  No anime found matching your query.[/yellow]\n")
        sys.exit(1)

    table = create_table(
        title=f"✨ Miruro Search Results ({len(results)}) ✨",
        columns=[
            ("Miruro ID", {"style": "cyan"}),
            ("Title", {"style": "bold bright_white"}),
            ("Format", {"style": "bright_green", "justify": "center"}),
            ("Episodes", {"style": "bright_cyan", "justify": "center"}),
            ("Duration", {"style": "bright_blue", "justify": "center"}),
            ("Score", {"style": "bright_yellow", "justify": "center"}),
            ("Status", {"style": "bright_magenta", "justify": "center"}),
        ],
        border_style="bright_blue",
        header_style="bold bright_magenta",
    )

    for r in results:
        fmt_badge = f"[bold on dark_blue] {r.format or 'TV'} [/]"
        score_val = f"⭐ {int(r.average_score)}%" if r.average_score else "N/A"
        table.add_row(
            str(r.id),
            r.title,
            fmt_badge,
            f"{r.episode_count} eps" if r.episode_count else "Ongoing",
            r.duration or "N/A",
            score_val,
            r.status or "N/A",
        )
    console.print(table)


def cmd_info(args):
    scraper = MiruroScraper(cache_enabled=not args.no_cache)
    with status_spinner(f"Fetching Miruro anime details for '{args.anime_id}'..."):
        try:
            series = scraper.get_series_detail(args.anime_id)
        except Exception as e:
            console.print(f"[red]❌ Error fetching series details: {e}[/red]")
            sys.exit(1)

    if not series:
        console.print(f"[red]❌ Series not found for ID: {args.anime_id}[/red]")
        sys.exit(1)

    title = series.title_english or series.title_romaji or "Unknown Title"
    genres_str = " • ".join(f"[bold bright_magenta]{g}[/]" for g in series.genres) if series.genres else "[dim]None[/dim]"
    studios_str = ", ".join(series.studios) if series.studios else "[dim]None[/dim]"
    score_str = f"⭐ [bold bright_yellow]{series.average_score}%[/bold bright_yellow]" if series.average_score else "[dim]N/A[/dim]"

    info_text = f"""[bold bright_white]🎬 Title (EN):[/bold bright_white]      [bold bright_yellow]{series.title_english or 'N/A'}[/bold bright_yellow]
[bold bright_white]🇯🇵 Title (Romaji):[/bold bright_white]  [white]{series.title_romaji or 'N/A'}[/white]
[bold bright_white]🔖 Miruro ID:[/bold bright_white]       [cyan]{series.id}[/cyan]
[bold bright_white]📺 Format:[/bold bright_white]          [bold on dark_blue] {series.format or 'TV'} [/]
[bold bright_white]📡 Status:[/bold bright_white]          [bright_blue]{series.status or 'N/A'}[/bright_blue]
[bold bright_white]📅 Year / Season:[/bold bright_white]   [bright_green]{series.season_year or 'N/A'} ({series.season or 'N/A'})[/bright_green]
[bold bright_white]⭐ Score:[/bold bright_white]           {score_str}
[bold bright_white]🎞️  Total Episodes:[/bold bright_white]  [bold bright_cyan]{len(series.episodes)}[/bold bright_cyan]
[bold bright_white]🏢 Studios:[/bold bright_white]        {studios_str}
[bold bright_white]🎭 Genres:[/bold bright_white]         {genres_str}

[bold bright_white]📖 Synopsis:[/bold bright_white]
[italic white]{series.description.strip() if series.description else 'No synopsis available.'}[/italic white]
"""
    console.print(
        Panel(
            info_text.strip(),
            title=f"[bold bright_cyan]✦ {title.upper()} ✦[/bold bright_cyan]",
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
            title=f"📺 Episode Catalog ({len(series.episodes)} Total{' - Showing First ' + str(ep_limit) if not show_all and len(series.episodes) > ep_limit else ''})",
            columns=[
                ("Ep #", {"style": "bold bright_yellow", "justify": "center", "width": 8}),
                ("Episode ID", {"style": "cyan"}),
                ("Title", {"style": "bold bright_white"}),
                ("Duration", {"style": "bright_blue", "justify": "center"}),
                ("Aired Date", {"style": "dim white", "justify": "center"}),
            ],
            border_style="cyan",
            header_style="bold bright_cyan",
        )

        for ep in ep_list:
            ep_num_str = f"{int(ep.episode_number)}" if ep.episode_number.is_integer() else f"{ep.episode_number}"
            dur_str = f"{ep.duration_minutes} min" if ep.duration_minutes else "N/A"
            ep_table.add_row(
                ep_num_str,
                str(ep.id),
                ep.title or f"Episode {ep_num_str}",
                dur_str,
                ep.aired_at or "N/A",
            )

        if not show_all and len(series.episodes) > ep_limit:
            remaining = len(series.episodes) - ep_limit
            ep_table.add_row("...", "...", f"[dim italic]+ {remaining} more episodes (use --all to show all)[/dim italic]", "...", "...")

        console.print(ep_table)


def cmd_episode(args):
    scraper = MiruroScraper(cache_enabled=not args.no_cache)
    with status_spinner(f"Fetching episode details for '{args.anime_id}' (Ep {args.ep})..."):
        try:
            ep = scraper.get_episode_detail(args.anime_id, float(args.ep))
        except Exception as e:
            console.print(f"[red]❌ Error fetching episode details: {e}[/red]")
            sys.exit(1)

    if not ep:
        console.print(f"[red]❌ Episode not found: {args.anime_id} (Episode {args.ep})[/red]")
        sys.exit(1)

    ep_num_str = f"{int(ep.episode_number)}" if ep.episode_number.is_integer() else f"{ep.episode_number}"
    panel_content = f"""[bold bright_white]🎬 Title:[/bold bright_white]               [bold bright_yellow]{ep.title}[/bold bright_yellow]
[bold bright_white]🔢 Episode Number:[/bold bright_white]      [bold bright_cyan]{ep_num_str}[/bold bright_cyan]
[bold bright_white]🔖 Anime ID:[/bold bright_white]            [cyan]{ep.anime_id}[/cyan]
[bold bright_white]💬 Subtitles Available:[/bold bright_white]  [bright_magenta]{len(ep.subtitles)} tracks[/bright_magenta]
[bold bright_white]🖥️  Streaming Servers:[/bold bright_white]    [bold bright_green]{len(ep.servers)} mirrors[/bold bright_green]
[bold bright_white]⬇️  Downloads Available:[/bold bright_white]  [bright_yellow]{len(ep.downloads)} files[/bright_yellow]
"""
    console.print(
        Panel(
            panel_content.strip(),
            title=f"[bold bright_green]✦ Episode Stream Details: Episode {ep_num_str} ✦[/bold bright_green]",
            border_style="bright_green",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    if ep.servers:
        srv_table = create_table(
            title=f"🖥️  Decrypted Streaming Mirrors & Direct Streams ({len(ep.servers)})",
            columns=[
                ("Server / Provider", {"style": "bold bright_white"}),
                ("Track", {"style": "bright_green", "justify": "center"}),
                ("Format", {"style": "bright_cyan", "justify": "center"}),
                ("Quality", {"style": "bright_yellow", "justify": "center"}),
                ("Direct / Embed URL", {"style": "underline cyan"}),
            ],
            border_style="bright_green",
            header_style="bold bright_green",
        )

        for s in ep.servers:
            track_badge = f"[bold on dark_blue] {s.track_type.upper()} [/]"
            srv_table.add_row(
                s.server_name,
                track_badge,
                s.format.upper(),
                s.quality or "N/A",
                s.url or s.embed_url or "N/A",
            )
        console.print(srv_table)

    if ep.subtitles:
        sub_table = create_table(
            title=f"💬 Subtitle Tracks ({len(ep.subtitles)})",
            columns=[
                ("Lang Code", {"style": "bright_green", "justify": "center", "width": 12}),
                ("Label", {"style": "bold bright_white"}),
                ("Format", {"style": "bright_yellow", "justify": "center", "width": 10}),
                ("Subtitle URL", {"style": "underline dim"}),
            ],
            border_style="bright_magenta",
            header_style="bold bright_magenta",
        )

        for sub in ep.subtitles:
            sub_table.add_row(sub.language, sub.label, sub.format or "vtt", sub.file)
        console.print(sub_table)


def cmd_crawl(args):
    scraper = MiruroScraper(cache_enabled=not args.no_cache)
    with status_spinner(f"Crawling Miruro anime '{args.anime_id}'..."):
        series = scraper.crawl_series(args.anime_id, max_episodes=args.max_episodes)
    console.print(f"[bold bright_green]✓ SUCCESS: Crawl complete! Saved series and {len(series.episodes)} episodes into SQLite database.[/bold bright_green]")


def cmd_stats(args):
    scraper = MiruroScraper()
    stats = scraper.storage.get_stats()
    content = f"""[bold bright_white]📚 Total Anime Series:[/bold bright_white]        [bold cyan]{stats.total_series}[/bold cyan]
[bold bright_white]📺 Total Episodes Registered:[/bold bright_white] [bold yellow]{stats.total_episodes}[/bold yellow]
[bold bright_white]✓ Completed Episodes:[/bold bright_white]         [bold green]{stats.completed_episodes}[/bold green]
[bold bright_white]⏳ Pending Episodes:[/bold bright_white]           [bright_yellow]{stats.pending_episodes}[/bright_yellow]
[bold bright_white]❌ Failed Episodes:[/bold bright_white]            [bold red]{stats.failed_episodes}[/bold red]
"""
    console.print(
        Panel(
            content.strip(),
            title="[bold bright_magenta]✦ Miruro SQLite Database Statistics ✦[/bold bright_magenta]",
            border_style="bright_magenta",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def cmd_export(args):
    scraper = MiruroScraper()
    with status_spinner(f"Exporting anime ID '{args.anime_id}' to JSON..."):
        out = scraper.storage.export_series_json(args.anime_id)
    if out:
        console.print(f"[green]✓ Successfully exported to {out}[/green]")
    else:
        console.print(f"[red]❌ Error: Anime ID '{args.anime_id}' not found in database.[/red]")


def main():
    parser = argparse.ArgumentParser(description="Miruro Production Anime Scraper CLI")
    parser.add_argument("--search", dest="query", nargs="?", const="", default=None, help="Search anime by title keyword")
    parser.add_argument("--limit", type=int, default=15, help="Search result limit (default: 15)")
    parser.add_argument("--info", dest="anime_id", help="Miruro anime ID or URL")
    parser.add_argument("--all", "-a", action="store_true", help="Show all episodes without truncating")
    parser.add_argument("--episode", dest="ep_anime_id", help="Anime ID or URL for playback extraction")
    parser.add_argument("--ep", dest="ep_val", default="1", help="Episode number (default: 1)")
    parser.add_argument("--crawl", dest="crawl_anime_id", help="Crawl anime series and playback sources to SQLite")
    parser.add_argument("--max-episodes", type=int, default=None, help="Limit number of episodes to crawl")
    parser.add_argument("--stats", action="store_true", help="View database statistics")
    parser.add_argument("--export", dest="export_anime_id", help="Export anime and stream details to JSON")
    parser.add_argument("--no-cache", action="store_true", help="Bypass disk cache")

    args = parser.parse_args()

    print_banner("Miruro", "GraphQL Anime Streaming & Episode Catalog")

    try:
        if args.query is not None:
            if not args.query.strip():
                console.print("[yellow]⚠️  No search query provided.[/yellow]")
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
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
