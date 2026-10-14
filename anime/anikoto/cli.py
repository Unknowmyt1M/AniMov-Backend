"""Rich Command-Line Interface for Anikoto Scraper."""

import argparse
import sys
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .scraper import AnikotoScraper
from .storage import AnikotoStorage

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console()


def print_search_results(results):
    if not results:
        console.print("[yellow]No anime found matching your query.[/yellow]")
        return

    table = Table(title=f"Anikoto Search Results ({len(results)})", header_style="bold magenta")
    table.add_column("Slug", style="cyan", no_wrap=False, overflow="fold")
    table.add_column("Title", style="bold white")
    table.add_column("Type", style="green")
    table.add_column("Episodes", style="yellow")
    table.add_column("Duration", style="blue")
    table.add_column("Score", style="magenta")

    for r in results:
        table.add_row(
            r.slug,
            r.title,
            r.anime_type or "N/A",
            r.episodes or "N/A",
            r.duration or "N/A",
            f"{r.score}/10" if r.score else "N/A",
        )
    console.print(table)


def print_series_detail(detail):
    if not detail:
        console.print("[red]Could not retrieve series details.[/red]")
        return

    info = f"""[bold cyan]Title:[/bold cyan] {detail.title}
[bold cyan]ID:[/bold cyan] {detail.anime_id}
[bold cyan]Status:[/bold cyan] {detail.status or 'N/A'}
[bold cyan]Genres:[/bold cyan] {', '.join(detail.genres) if detail.genres else 'N/A'}
[bold cyan]Total Episodes:[/bold cyan] {detail.total_episodes}
[bold cyan]Synopsis:[/bold cyan] {detail.synopsis[:200] + '...' if detail.synopsis else 'N/A'}
"""
    console.print(Panel(info, title=f"Series: {detail.title}", border_style="cyan"))

    if detail.episodes:
        table = Table(title=f"Episodes ({len(detail.episodes)})", header_style="bold cyan")
        table.add_column("Ep #", style="yellow")
        table.add_column("Episode ID", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Sub", style="green")
        table.add_column("Dub", style="magenta")

        for ep in detail.episodes[:25]:
            table.add_row(
                str(ep.episode_num),
                ep.id,
                ep.title,
                "YES" if ep.has_sub else "NO",
                "YES" if ep.has_dub else "NO",
            )
        if len(detail.episodes) > 25:
            table.add_row("...", "...", f"(+ {len(detail.episodes) - 25} more)", "...", "...")
        console.print(table)


def print_stream_result(stream):
    if not stream:
        console.print("[red]Could not retrieve stream details.[/red]")
        return

    content = f"""[bold green]Server:[/bold green] {stream.server_name} ({stream.server_type.upper()})
[bold green]Embed URL:[/bold green] {stream.embed_url}
[bold cyan]Master m3u8:[/bold cyan] [underline]{stream.master_m3u8 or 'Decryption Failed / Direct Only'}[/underline]
"""
    if stream.skip_data:
        intro = stream.skip_data.intro
        outro = stream.skip_data.outro
        if intro:
            content += f"[bold yellow]Intro:[/bold yellow] {intro.start}s - {intro.end}s\n"
        if outro:
            content += f"[bold yellow]Outro:[/bold yellow] {outro.start}s - {outro.end}s\n"

    if stream.subtitles:
        content += f"[bold magenta]Subtitles:[/bold magenta] {len(stream.subtitles)} tracks ("
        content += ", ".join([f"{s.label}" for s in stream.subtitles[:5]])
        if len(stream.subtitles) > 5:
            content += f", +{len(stream.subtitles) - 5} more"
        content += ")\n"

    console.print(Panel(content, title=f"Stream: Episode {stream.episode_num}", border_style="green"))


def main():
    parser = argparse.ArgumentParser(description="Anikoto Anime Scraper CLI")
    parser.add_argument("--search", "-s", nargs="?", const="", default=None, help="Search anime by title")
    parser.add_argument("--detail", "-d", type=str, help="Get series detail by slug or URL")
    parser.add_argument("--refresh", action="store_true", help="Bypass cache and fetch fresh series detail")
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

    try:
        if args.search is not None:
            if not args.search.strip():
                console.print("[yellow]No search query provided.[/yellow]")
                sys.exit(1)
            results = scraper.search(args.search)
            print_search_results(results)
            if not results:
                sys.exit(1)

        elif args.detail:
            detail = scraper.get_series_detail(args.detail, use_cache=not args.refresh)
            print_series_detail(detail)
            if not detail:
                sys.exit(1)

        elif args.episode:
            detail = scraper.get_series_detail(args.episode, use_cache=not args.refresh)
            if not detail or not detail.episodes:
                console.print("[red]Could not load episodes for anime.[/red]")
                sys.exit(1)

            target_ep = next((ep for ep in detail.episodes if ep.episode_num == args.ep), detail.episodes[0])
            servers = scraper.get_episode_servers(target_ep.server_param)
            matching = [s for s in servers if s.server_type == args.server_type] or servers

            if not matching:
                console.print(f"[red]No servers found for episode {args.ep}.[/red]")
                sys.exit(1)

            srv = matching[0]
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
            detail = scraper.crawl_series(args.crawl, max_episodes=args.max_episodes, server_type=args.server_type)
            print_series_detail(detail)
            if not detail:
                sys.exit(1)

        elif args.stats:
            stats = storage.get_stats()
            console.print(
                Panel(
                    f"Total Series: {stats.total_series}\nTotal Episodes: {stats.total_episodes}\nTotal Streams: {stats.total_streams}\nLast Crawled: {stats.last_crawled_at or 'Never'}",
                    title="Anikoto Local Storage Stats",
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
