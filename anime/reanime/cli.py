"""Rich Command-Line Interface for ReAnime Scraper."""

import argparse
import sys
import json
from pathlib import Path
from rich.panel import Panel

from common.ui import (
    console,
    print_banner,
    status_spinner,
    create_table,
    box,
)

try:
    from .scraper import ReAnimeScraper
    from .storage import ReAnimeStorage
except ImportError:
    from anime.reanime.scraper import ReAnimeScraper
    from anime.reanime.storage import ReAnimeStorage


def print_search_results(results):
    if not results:
        console.print("\n[yellow]⚠️  No anime found matching your query.[/yellow]\n")
        return

    table = create_table(
        title=f"✨ ReAnime Search Results ({len(results)}) ✨",
        columns=[
            ("Slug", {"style": "cyan"}),
            ("Title", {"style": "bold bright_white"}),
            ("Type", {"style": "bright_green", "justify": "center"}),
            ("Episodes", {"style": "bright_yellow", "justify": "center"}),
            ("Duration", {"style": "bright_blue", "justify": "center"}),
            ("Score", {"style": "bright_magenta", "justify": "center"}),
        ],
        border_style="bright_blue",
        header_style="bold bright_magenta",
    )

    for r in results:
        type_badge = f"[bold on dark_blue] {r.anime_type or 'TV'} [/]"
        score_val = f"⭐ {r.score}/10" if r.score else "N/A"
        table.add_row(
            r.slug,
            r.title,
            type_badge,
            str(r.episodes or "N/A"),
            r.duration or "N/A",
            score_val,
        )
    console.print(table)


def print_series_detail(detail, show_all: bool = False, limit: int = 50):
    if not detail:
        console.print("\n[red]❌ Could not retrieve series details.[/red]\n")
        return

    genres_str = " • ".join(f"[bold bright_magenta]{g}[/]" for g in detail.genres) if detail.genres else "[dim]N/A[/dim]"
    score_str = f"⭐ [bold bright_yellow]{detail.average_score}/10[/bold bright_yellow]" if detail.average_score else "[dim]N/A[/dim]"
    season_str = f"{detail.season} {detail.season_year}" if detail.season else "N/A"

    info = f"""[bold bright_white]🎬 Title:[/bold bright_white]         [bold bright_yellow]{detail.title}[/bold bright_yellow]
[bold bright_white]🔖 Slug:[/bold bright_white]          [cyan]{detail.slug}[/cyan]
[bold bright_white]🆔 AniList / MAL:[/bold bright_white] [dim]{detail.anilist_id or 'N/A'}[/dim] / [dim]{detail.mal_id or 'N/A'}[/dim]
[bold bright_white]📡 Status:[/bold bright_white]        [bright_blue]{detail.status or 'N/A'}[/bright_blue]
[bold bright_white]⭐ Score:[/bold bright_white]         {score_str}
[bold bright_white]📅 Season:[/bold bright_white]        [bright_green]{season_str}[/bright_green]
[bold bright_white]🎭 Genres:[/bold bright_white]        {genres_str}
[bold bright_white]🎞️  Total Episodes:[/bold bright_white] [bold bright_cyan]{detail.total_episodes}[/bold bright_cyan]

[bold bright_white]📖 Synopsis:[/bold bright_white]
[italic white]{detail.synopsis.strip() if detail.synopsis else 'N/A'}[/italic white]
"""
    console.print(
        Panel(
            info.strip(),
            title=f"[bold bright_cyan]✦ {detail.title.upper()} ✦[/bold bright_cyan]",
            border_style="bright_cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    if detail.episodes:
        ep_list = detail.episodes if show_all else detail.episodes[:limit]
        table = create_table(
            title=f"📺 Episodes ({len(detail.episodes)} Total{' - Showing First ' + str(limit) if not show_all and len(detail.episodes) > limit else ''})",
            columns=[
                ("Ep #", {"style": "bold bright_yellow", "justify": "center", "width": 8}),
                ("ID", {"style": "cyan"}),
                ("Title", {"style": "bold bright_white"}),
                ("Sub", {"style": "bright_green", "justify": "center", "width": 8}),
                ("Dub", {"style": "bright_magenta", "justify": "center", "width": 8}),
                ("Filler", {"style": "bright_red", "justify": "center", "width": 8}),
                ("Aired", {"style": "dim white", "justify": "center"}),
            ],
            border_style="cyan",
            header_style="bold bright_cyan",
        )

        for ep in ep_list:
            sub_badge = "[bold green]YES[/]" if ep.is_subbed else "[dim]-[/dim]"
            dub_badge = "[bold magenta]YES[/]" if ep.is_dubbed else "[dim]-[/dim]"
            filler_badge = "[bold red]YES[/]" if ep.is_filler else "[dim]-[/dim]"
            table.add_row(
                str(ep.episode_num),
                ep.id,
                ep.title or f"Episode {ep.episode_num}",
                sub_badge,
                dub_badge,
                filler_badge,
                ep.aired_at or "N/A",
            )

        if not show_all and len(detail.episodes) > limit:
            remaining = len(detail.episodes) - limit
            table.add_row("...", "...", f"[dim italic]+ {remaining} more episodes (use --all to show all)[/dim italic]", "...", "...", "...", "...")

        console.print(table)


def print_stream_result(stream):
    if not stream:
        console.print("\n[red]❌ Could not retrieve stream details.[/red]\n")
        return

    status_color = "bright_green" if stream.status == "available" else "bright_yellow"
    info = f"""[bold bright_white]🔖 Slug:[/bold bright_white]       [cyan]{stream.slug}[/cyan]
[bold bright_white]🔢 Episode:[/bold bright_white]    [bold yellow]Episode {stream.episode_num}[/bold yellow]
[bold bright_white]📡 Status:[/bold bright_white]     [{status_color}]{stream.status.upper()}[/{status_color}]
[bold bright_white]🔗 Embed URL:[/bold bright_white]  [underline cyan]{stream.embed_url or 'None'}[/underline cyan]
[bold bright_white]💬 Message:[/bold bright_white]    [white]{stream.message or 'N/A'}[/white]
"""
    console.print(
        Panel(
            info.strip(),
            title=f"[bold bright_green]✦ ReAnime Stream - Ep {stream.episode_num} ✦[/bold bright_green]",
            border_style=status_color,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def print_stats(stats):
    content = f"""[bold bright_white]📚 Total Series Cached:[/bold bright_white]   [bold cyan]{stats.total_series}[/bold cyan]
[bold bright_white]📺 Total Episodes Cached:[/bold bright_white] [bold yellow]{stats.total_episodes}[/bold yellow]
[bold bright_white]🎥 Total Streams Cached:[/bold bright_white]  [bold green]{stats.total_streams}[/bold green]
[bold bright_white]⏱️  Last Crawled:[/bold bright_white]          [dim]{stats.last_crawled_at or 'Never'}[/dim]"""
    console.print(
        Panel(
            content.strip(),
            title="[bold bright_magenta]✦ ReAnime Database Cache Stats ✦[/bold bright_magenta]",
            border_style="bright_magenta",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def main():
    parser = argparse.ArgumentParser(description="ReAnime (reanime.to) CLI Scraper")
    parser.add_argument("--search", "-s", nargs="?", const="", default=None, help="Search anime by title")
    parser.add_argument("--detail", "-d", type=str, help="Get full series metadata and episode roster by slug")
    parser.add_argument("--all", "-a", action="store_true", help="Show all episodes without truncating")
    parser.add_argument("--limit", type=int, default=50, help="Episode table display limit (default: 50)")
    parser.add_argument("--episode", "-e", type=str, help="Anime slug for stream extraction")
    parser.add_argument("--ep", type=int, default=1, help="Episode number (default: 1)")
    parser.add_argument("--stats", action="store_true", help="Show SQLite cache statistics")
    parser.add_argument("--no-cache", action="store_true", help="Bypass SQLite cache")
    parser.add_argument("--refresh", action="store_true", help="Bypass SQLite cache and fetch fresh data")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")

    args = parser.parse_args()
    scraper = ReAnimeScraper()
    use_cache = not (args.no_cache or args.refresh)

    if not args.json:
        print_banner("ReAnime", "reanime.to Fast Streaming & Episode API")

    try:
        if args.search is not None:
            if not args.search.strip():
                console.print("[yellow]⚠️  No search query provided.[/yellow]")
                sys.exit(1)
            with status_spinner(f"Searching ReAnime for '{args.search}'..."):
                results = scraper.search(args.search)
            if args.json:
                print(json.dumps([r.model_dump() for r in results], indent=2))
            else:
                print_search_results(results)
            if not results:
                sys.exit(1)

        elif args.detail:
            with status_spinner(f"Fetching series detail for '{args.detail}'..."):
                detail = scraper.get_series_detail(args.detail, use_cache=use_cache)
            if not detail:
                if args.json:
                    print(json.dumps({"error": "Anime not found"}, indent=2))
                else:
                    console.print("[red]❌ Could not retrieve series details (Anime not found / 404).[/red]")
                sys.exit(1)

            if args.json:
                print(detail.model_dump_json(indent=2))
            else:
                print_series_detail(detail, show_all=args.all, limit=args.limit)

        elif args.episode:
            with status_spinner(f"Extracting stream for '{args.episode}' Ep {args.ep}..."):
                stream = scraper.get_episode_stream(args.episode, args.ep, use_cache=use_cache)
            if not stream:
                if args.json:
                    print(json.dumps({"error": "Stream not found"}, indent=2))
                else:
                    console.print(f"[red]❌ Could not retrieve stream for episode {args.ep}.[/red]")
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
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        sys.exit(1)
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
