"""Rich Command-Line Interface for Anikoto Scraper."""

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
    from .scraper import AnikotoScraper
    from .storage import AnikotoStorage
except ImportError:
    from anime.anikoto.scraper import AnikotoScraper
    from anime.anikoto.storage import AnikotoStorage


def print_search_results(results):
    if not results:
        console.print("\n[yellow]⚠️  No anime found matching your query.[/yellow]\n")
        return

    table = create_table(
        title=f"✨ Anikoto Search Results ({len(results)}) ✨",
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
    card_content = f"""[bold bright_white]🎬 Title:[/bold bright_white]         [bold bright_yellow]{detail.title}[/bold bright_yellow]
[bold bright_white]🔖 Anime ID:[/bold bright_white]      [cyan]{detail.anime_id}[/cyan]
[bold bright_white]📡 Status:[/bold bright_white]        [bright_blue]{detail.status or 'N/A'}[/bright_blue]
[bold bright_white]🎭 Genres:[/bold bright_white]        {genres_str}
[bold bright_white]🎞️  Total Episodes:[/bold bright_white] [bold bright_cyan]{detail.total_episodes}[/bold bright_cyan]

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
        ep_list = detail.episodes if show_all else detail.episodes[:limit]
        table = create_table(
            title=f"📺 Episodes ({len(detail.episodes)} Total{' - Showing First ' + str(limit) if not show_all and len(detail.episodes) > limit else ''})",
            columns=[
                ("Ep #", {"style": "bold bright_yellow", "justify": "center", "width": 8}),
                ("Episode ID", {"style": "cyan"}),
                ("Title", {"style": "bold bright_white"}),
                ("Sub", {"style": "bright_green", "justify": "center", "width": 8}),
                ("Dub", {"style": "bright_magenta", "justify": "center", "width": 8}),
            ],
            border_style="cyan",
            header_style="bold bright_cyan",
        )

        for ep in ep_list:
            sub_badge = "[bold green]YES[/]" if ep.has_sub else "[dim]NO[/dim]"
            dub_badge = "[bold magenta]YES[/]" if ep.has_dub else "[dim]NO[/dim]"
            table.add_row(
                str(ep.episode_num),
                ep.id,
                ep.title or f"Episode {ep.episode_num}",
                sub_badge,
                dub_badge,
            )

        if not show_all and len(detail.episodes) > limit:
            remaining = len(detail.episodes) - limit
            table.add_row("...", "...", f"[dim italic]+ {remaining} more episodes (use --all to show all)[/dim italic]", "...", "...")

        console.print(table)


def print_stream_result(stream):
    if not stream:
        console.print("\n[red]❌ Could not retrieve stream details.[/red]\n")
        return

    content = f"""[bold bright_white]🖥️  Server:[/bold bright_white]      [bold bright_green]{stream.server_name}[/bold bright_green] ([bold cyan]{stream.server_type.upper()}[/bold cyan])
[bold bright_white]🔗 Embed URL:[/bold bright_white]   [underline cyan]{stream.embed_url}[/underline cyan]
[bold bright_white]🎥 Master m3u8:[/bold bright_white] [underline yellow]{stream.master_m3u8 or 'Decryption Failed / Direct Only'}[/underline yellow]
"""
    if stream.skip_data:
        intro = stream.skip_data.intro
        outro = stream.skip_data.outro
        if intro:
            content += f"[bold bright_white]⏩ Intro Skip:[/bold bright_white]  [bright_yellow]{intro.start}s - {intro.end}s[/bright_yellow]\n"
        if outro:
            content += f"[bold bright_white]⏩ Outro Skip:[/bold bright_white]  [bright_yellow]{outro.start}s - {outro.end}s[/bright_yellow]\n"

    if stream.subtitles:
        sub_names = ", ".join([f"{s.label}" for s in stream.subtitles[:5]])
        if len(stream.subtitles) > 5:
            sub_names += f" (+{len(stream.subtitles) - 5} more)"
        content += f"[bold bright_white]💬 Subtitles:[/bold bright_white]   [bright_magenta]{len(stream.subtitles)} tracks[/bright_magenta] ({sub_names})\n"

    console.print(
        Panel(
            content.strip(),
            title=f"[bold bright_green]✦ Stream: Episode {stream.episode_num} ✦[/bold bright_green]",
            border_style="bright_green",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def main():
    parser = argparse.ArgumentParser(description="Anikoto Anime Scraper CLI")
    parser.add_argument("--search", "-s", nargs="?", const="", default=None, help="Search anime by title")
    parser.add_argument("--detail", "-d", type=str, help="Get series detail by slug or URL")
    parser.add_argument("--refresh", action="store_true", help="Bypass cache and fetch fresh series detail")
    parser.add_argument("--all", "-a", action="store_true", help="Show all episodes without truncating")
    parser.add_argument("--limit", type=int, default=50, help="Episode table display limit (default: 50)")
    parser.add_argument("--episode", "-e", type=str, help="Anime slug or URL to stream")
    parser.add_argument("--ep", type=int, default=1, help="Episode number (default: 1)")
    parser.add_argument("--server-type", choices=["sub", "dub"], default="sub", help="Preferred server audio type")
    parser.add_argument("--crawl", "-c", type=str, help="Crawl series and pre-cache episodes")
    parser.add_argument("--max-episodes", type=int, default=None, help="Limit number of episodes to crawl")
    parser.add_argument("--stats", action="store_true", help="Display local SQLite cache stats")
    parser.add_argument("--export", type=str, help="Export cached series to JSON file")

    args = parser.parse_args()
    scraper = AnikotoScraper()
    storage = AnikotoStorage()

    print_banner("Anikoto", "Anime Streaming & Episode Scraper")

    try:
        if args.search is not None:
            if not args.search.strip():
                console.print("[yellow]⚠️  No search query provided.[/yellow]")
                sys.exit(1)
            with status_spinner(f"Searching Anikoto for '{args.search}'..."):
                results = scraper.search(args.search)
            print_search_results(results)
            if not results:
                sys.exit(1)

        elif args.detail:
            with status_spinner(f"Fetching series details for '{args.detail}'..."):
                detail = scraper.get_series_detail(args.detail, use_cache=not args.refresh)
            print_series_detail(detail, show_all=args.all, limit=args.limit)
            if not detail:
                sys.exit(1)

        elif args.episode:
            with status_spinner(f"Loading anime episodes for '{args.episode}'..."):
                detail = scraper.get_series_detail(args.episode, use_cache=not args.refresh)
            if not detail or not detail.episodes:
                console.print("[red]❌ Could not load episodes for anime.[/red]")
                sys.exit(1)

            target_ep = next((ep for ep in detail.episodes if ep.episode_num == args.ep), detail.episodes[0])
            with status_spinner(f"Fetching servers for Episode {target_ep.episode_num}..."):
                servers = scraper.get_episode_servers(target_ep.server_param)
            matching = [s for s in servers if s.server_type == args.server_type] or servers

            if not matching:
                console.print(f"[red]❌ No servers found for episode {args.ep}.[/red]")
                sys.exit(1)

            srv = matching[0]
            with status_spinner(f"Resolving stream from '{srv.name}' ({srv.server_type})..."):
                stream = scraper.get_stream_detail(
                    episode_id=target_ep.id,
                    episode_num=target_ep.episode_num,
                    link_id=srv.link_id,
                    server_name=srv.name,
                    server_type=srv.server_type,
                )
            print_stream_result(stream)
            if not stream:
                sys.exit(1)

        elif args.crawl:
            with status_spinner(f"Crawling series '{args.crawl}'..."):
                detail = scraper.crawl_series(args.crawl, max_episodes=args.max_episodes, server_type=args.server_type)
            print_series_detail(detail, show_all=args.all, limit=args.limit)
            if not detail:
                sys.exit(1)

        elif args.stats:
            stats = storage.get_stats()
            stats_content = f"""[bold bright_white]📚 Total Series:[/bold bright_white]   [bold cyan]{stats.total_series}[/bold cyan]
[bold bright_white]📺 Total Episodes:[/bold bright_white] [bold yellow]{stats.total_episodes}[/bold yellow]
[bold bright_white]🎥 Total Streams:[/bold bright_white]  [bold green]{stats.total_streams}[/bold green]
[bold bright_white]⏱️  Last Crawled:[/bold bright_white]   [dim]{stats.last_crawled_at or 'Never'}[/dim]"""
            console.print(
                Panel(
                    stats_content,
                    title="[bold bright_magenta]✦ Anikoto Local Storage Stats ✦[/bold bright_magenta]",
                    border_style="magenta",
                    box=box.ROUNDED,
                    padding=(1, 2),
                )
            )

        elif args.export:
            storage.export_json(Path(args.export))
            console.print(f"[green]✓ Successfully exported data to {args.export}[/green]")

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
