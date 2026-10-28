"""Rich Command-Line Interface for AnimeSalt Scraper."""

import argparse
import sys
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich import box

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .scraper import AnimeSaltScraper
from .storage import AnimeSaltStorage

console = Console()

BANNER_ART = r"""
    ___          _ __  ___          
   /   |  ____  (_)  |/  /___  _  __
  / /| | / __ \/ / /|_/ / __ \| |/ /
 / ___ |/ / / / / /  / / /_/ /|   / 
/_/  |_/_/ /_/_/_/  /_/\____/ |_/  
"""


def print_banner():
    logo = Text(BANNER_ART, style="bold bright_cyan")
    tagline = Text("⚡ ANIMESALT ⚡  |  Multi-Audio Dubs & High-Speed Stream Engine", style="bold bright_yellow")
    panel = Panel(
        Align.center(Text.assemble(logo, "\n", tagline)),
        border_style="bright_magenta",
        box=box.ROUNDED,
        padding=(0, 2),
    )
    console.print(panel)


def print_search_results(results):
    if not results:
        console.print("\n[yellow]⚠️  No anime found matching your query.[/yellow]\n")
        return

    table = Table(
        title=f"✨ AnimeSalt Search Results ({len(results)}) ✨",
        header_style="bold bright_magenta",
        border_style="bright_blue",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("Slug", style="cyan", no_wrap=False, overflow="fold")
    table.add_column("Title", style="bold bright_white")
    table.add_column("Type", style="bright_green", justify="center")
    table.add_column("Episodes", style="bright_yellow", justify="center")
    table.add_column("Duration", style="bright_blue", justify="center")

    for r in results:
        media_badge = f"[bold on dark_magenta] {r.anime_type} [/]" if "Movie" in (r.anime_type or "") else f"[bold on dark_blue] {r.anime_type or 'TV Series'} [/]"
        table.add_row(
            r.slug,
            r.title,
            media_badge,
            r.episodes or "N/A",
            r.duration or "N/A",
        )
    console.print(table)


def print_series_detail(
    detail,
    season: Optional[int] = None,
    show_all: bool = False,
    limit: int = 25,
):
    if not detail:
        console.print("\n[red]❌ Could not retrieve series details.[/red]\n")
        return

    seasons_str = ", ".join(str(s) for s in detail.seasons) if detail.seasons else "1"
    lang_badges = " ".join(f"[bold black on bright_cyan] {l} [/]" for l in detail.languages) if getattr(detail, "languages", None) else "[dim]N/A[/dim]"
    genre_str = " • ".join(f"[bold bright_magenta]{g}[/]" for g in detail.genres) if detail.genres else "[dim]N/A[/dim]"

    card_content = f"""[bold bright_white]🎬 Title:[/bold bright_white]         [bold bright_yellow]{detail.title}[/bold bright_yellow]
[bold bright_white]🔖 Slug:[/bold bright_white]          [cyan]{detail.slug}[/cyan]
[bold bright_white]📅 Release Year:[/bold bright_white]  [bright_green]{getattr(detail, 'year', None) or 'N/A'}[/bright_green]
[bold bright_white]⏱️  Duration:[/bold bright_white]      [bright_blue]{getattr(detail, 'duration', None) or 'N/A'}[/bright_blue]
[bold bright_white]🌐 Languages:[/bold bright_white]     {lang_badges}
[bold bright_white]🎭 Genres:[/bold bright_white]        {genre_str}
[bold bright_white]📦 Total Seasons:[/bold bright_white] [bold bright_yellow]{detail.total_seasons or len(detail.seasons) or 1} Seasons[/bold bright_yellow] [dim]({seasons_str})[/dim]
[bold bright_white]🎞️  Episodes:[/bold bright_white]      [bold bright_cyan]{detail.total_episodes} Episodes Total[/bold bright_cyan]

[bold bright_white]📖 Synopsis:[/bold bright_white]
[italic white]{detail.synopsis if detail.synopsis else 'N/A'}[/italic white]
"""
    console.print(
        Panel(
            card_content.strip(),
            title=f"[bold bright_cyan]✦ {detail.title.upper()} ✦[/bold bright_cyan]",
            border_style="bright_cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    if detail.episodes:
        episodes_to_display = detail.episodes
        if season is not None:
            episodes_to_display = [ep for ep in detail.episodes if ep.season_num == season]
            if not episodes_to_display:
                console.print(f"[yellow]⚠️  No episodes found for Season {season}. Available seasons: {seasons_str}[/yellow]")
                return

        table_title = f"📺 Episodes ({len(episodes_to_display)})"
        if season is not None:
            table_title = f"📺 Season {season} Episodes ({len(episodes_to_display)})"

        table = Table(
            title=table_title,
            header_style="bold bright_cyan",
            border_style="cyan",
            box=box.ROUNDED,
            show_lines=True,
        )
        table.add_column("Season", style="bold bright_yellow", justify="center", width=8)
        table.add_column("Ep #", style="bold bright_green", justify="center", width=8)
        table.add_column("Slug", style="cyan", no_wrap=False, overflow="fold")
        table.add_column("Title", style="bold white")

        if show_all or season is not None:
            for ep in episodes_to_display:
                table.add_row(
                    str(ep.season_num),
                    str(ep.episode_num),
                    ep.slug,
                    ep.title,
                )
        else:
            display_count = min(limit, len(episodes_to_display))
            for ep in episodes_to_display[:display_count]:
                table.add_row(
                    str(ep.season_num),
                    str(ep.episode_num),
                    ep.slug,
                    ep.title,
                )
            if len(episodes_to_display) > display_count:
                remaining = len(episodes_to_display) - display_count
                table.add_row("...", "...", "...", f"(+ {remaining} more)")

        console.print(table)

        if not show_all and season is None and len(episodes_to_display) > limit:
            console.print(
                f"[dim]💡 Tip: Showing first {limit} episodes. Use [bold white]--all[/bold white] to view all {len(detail.episodes)} episodes, or [bold white]--season <num>[/bold white] to view a specific season.[/dim]\n"
            )


def print_episode_streams(ep):
    if not ep:
        console.print("\n[red]❌ Could not retrieve episode streams.[/red]\n")
        return

    content = f"""[bold bright_white]📺 Episode:[/bold bright_white]        [bold bright_yellow]Season {ep.season_num}, Episode {ep.episode_num}[/bold bright_yellow]
[bold bright_white]🎬 Title:[/bold bright_white]          [bold bright_white]{ep.title}[/bold bright_white]
[bold bright_white]🚀 Primary Player:[/bold bright_white] [cyan]{ep.iframe_url or 'None'}[/cyan]
[bold bright_white]🔗 Direct Link:[/bold bright_white]    [cyan]{ep.link}[/cyan]
"""
    console.print(
        Panel(
            content.strip(),
            title=f"[bold bright_green]✦ {ep.slug.upper()} ✦[/bold bright_green]",
            border_style="bright_green",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    if ep.audio_streams:
        srv_table = Table(
            title="🔊 Available Audio Dubs & Streaming Mirrors",
            header_style="bold bright_yellow",
            border_style="bright_yellow",
            box=box.ROUNDED,
            show_lines=True,
        )
        srv_table.add_column("Language / Mirror", style="bold bright_cyan", width=22)
        srv_table.add_column("Stream URL", style="underline bright_white")
        for s in ep.audio_streams:
            srv_table.add_row(f"⚡ {s.language}", s.link)
        console.print(srv_table)
    else:
        console.print("[yellow]⚠️  No parsed multi-audio streams found.[/yellow]")


def main():
    parser = argparse.ArgumentParser(description="AnimeSalt Scraper CLI")
    parser.add_argument("--search", "-s", nargs="?", const="", default=None, help="Search anime by title")
    parser.add_argument("--detail", "-d", type=str, help="Get series detail by slug or URL")
    parser.add_argument("--all", "-a", action="store_true", help="Display all episodes without truncating")
    parser.add_argument("--season", "-sn", type=int, default=None, help="Filter episode display by season number")
    parser.add_argument("--limit", "-l", type=int, default=25, help="Number of episodes to display (default: 25)")
    parser.add_argument("--refresh", action="store_true", help="Bypass cache and fetch fresh series detail")
    parser.add_argument("--episode", "-e", type=str, help="Episode slug or URL (e.g. solo-leveling-1x1)")
    parser.add_argument("--crawl", "-c", type=str, help="Crawl series and pre-cache episodes")
    parser.add_argument("--max-episodes", type=int, default=None, help="Limit number of episodes to crawl")
    parser.add_argument("--stats", action="store_true", help="Display local SQLite cache stats")
    parser.add_argument("--export", type=str, help="Export cached series to JSON file")

    args = parser.parse_args()
    scraper = AnimeSaltScraper()
    storage = AnimeSaltStorage()

    print_banner()

    try:
        if args.search is not None:
            with console.status(f"[bold bright_cyan]🔍 Searching AnimeSalt catalog for '[bold white]{args.search}[/bold white]'...[/bold bright_cyan]", spinner="dots12"):
                results = scraper.search(args.search)
            print_search_results(results)
            if not results:
                sys.exit(1)

        elif args.detail:
            with console.status(f"[bold bright_magenta]✨ Syncing series details & crawling all seasons for '[bold white]{args.detail}[/bold white]'...[/bold bright_magenta]", spinner="aesthetic"):
                detail = scraper.get_series_detail(args.detail, use_cache=not args.refresh)
            if not detail:
                console.print("\n[red]❌ Could not retrieve series details.[/red]\n")
                sys.exit(1)
            print_series_detail(detail, season=args.season, show_all=args.all, limit=args.limit)

        elif args.episode:
            with console.status(f"[bold bright_green]🚀 Resolving multi-audio streams & player embeds for '[bold white]{args.episode}[/bold white]'...[/bold bright_green]", spinner="arc"):
                ep = scraper.get_episode_streams(args.episode)
            if not ep:
                console.print("\n[red]❌ Could not retrieve episode streams.[/red]\n")
                sys.exit(1)
            print_episode_streams(ep)

        elif args.crawl:
            with console.status(f"[bold bright_yellow]⚡ Crawling series episodes for '[bold white]{args.crawl}[/bold white]'...[/bold bright_yellow]", spinner="bouncingBar"):
                detail = scraper.crawl_series(args.crawl, max_episodes=args.max_episodes)
            if not detail:
                sys.exit(1)
            print_series_detail(detail, season=args.season, show_all=args.all, limit=args.limit)

        elif args.stats:
            stats = storage.get_stats()
            console.print(
                Panel(
                    f"Total Series: {stats.total_series}\nTotal Episodes: {stats.total_episodes}\nTotal Stream Sets: {stats.total_streams}\nLast Crawled: {stats.last_crawled_at or 'Never'}",
                    title="AnimeSalt Local Storage Stats",
                    border_style="magenta",
                    box=box.ROUNDED,
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
