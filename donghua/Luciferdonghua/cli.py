"""
CLI Interface for Lucifer Donghua Scraper.
Supports searching, viewing show metadata, character lists,
inspecting mirror video players, and full series crawling.
"""

import argparse
import json
import sys
from pathlib import Path

# Fix Windows console UTF-8 encoding for Asian characters
try:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .scraper import LuciferDonghuaScraper
from .storage import LuciferStorage
from .config import OUTPUT_DIR

console = Console(safe_box=True)


def print_lucifer_donghua_card(donghua):
    """Renders formatted panel with Lucifer Donghua metadata."""
    characters_str = ", ".join([f"{c.name} ({c.role})" for c in donghua.characters[:5]]) if donghua.characters else "N/A"
    producers_str = ", ".join(donghua.producers) if donghua.producers else "N/A"

    meta_info = f"""[bold cyan]Title:[/bold cyan] {donghua.title}
[bold cyan]Alternate Titles:[/bold cyan] {donghua.alternative_titles or 'N/A'}
[bold cyan]Status:[/bold cyan] {donghua.status or 'N/A'} | [bold cyan]Rating:[/bold cyan] {donghua.rating or 'N/A'} | [bold cyan]Type:[/bold cyan] {donghua.type}
[bold cyan]Studio:[/bold cyan] {donghua.studio or 'N/A'} | [bold cyan]Director:[/bold cyan] {donghua.director or 'N/A'} | [bold cyan]Producers:[/bold cyan] {producers_str}
[bold cyan]Released Year:[/bold cyan] {donghua.released_year or 'N/A'} | [bold cyan]Duration:[/bold cyan] {donghua.duration or 'N/A'}
[bold cyan]Expected Episodes:[/bold cyan] {donghua.total_episodes_expected or 'N/A'} | [bold cyan]Scraped:[/bold cyan] {donghua.total_scraped_episodes}
[bold cyan]Site Post Date:[/bold cyan] {donghua.site_released_on or 'N/A'} | [bold cyan]Updated:[/bold cyan] {donghua.site_updated_on or 'N/A'}
[bold cyan]Genres:[/bold cyan] {', '.join(donghua.genres) if donghua.genres else 'N/A'}
[bold cyan]Followers:[/bold cyan] {donghua.followers or 'N/A'}
[bold cyan]Characters:[/bold cyan] {characters_str}
[bold cyan]Poster:[/bold cyan] {donghua.poster_url or 'N/A'}

[bold yellow]Synopsis:[/bold yellow]
{donghua.synopsis[:300] + '...' if donghua.synopsis and len(donghua.synopsis) > 300 else (donghua.synopsis or 'N/A')}
"""
    console.print(Panel(meta_info, title=f"[bold green]{donghua.title}[/bold green]", border_style="green"))


def main():
    parser = argparse.ArgumentParser(description="Lucifer Donghua Production Scraper CLI")
    parser.add_argument("--search", type=str, nargs="?", const="", default=None, help="Search for Donghua by query")
    parser.add_argument("--info", type=str, help="Get series metadata and episode table by slug or URL")
    parser.add_argument("--episode", type=str, help="Extract streaming mirrors and download links from episode URL")
    parser.add_argument("--crawl", type=str, help="Crawl a series and its episode streams into SQLite database")
    parser.add_argument("--max-episodes", type=int, default=None, help="Limit number of episodes to crawl")
    parser.add_argument("--catalog", action="store_true", help="Browse catalog pages")
    parser.add_argument("--pages", type=int, default=1, help="Number of catalog pages to fetch")
    parser.add_argument("--stats", action="store_true", help="Display SQLite storage stats")
    parser.add_argument("--retry-failed", action="store_true", help="Reset all failed tasks for retry")
    parser.add_argument("--export", type=str, help="Export a series from SQLite to JSON file")
    parser.add_argument("--sniff", action="store_true", help="Enable Playwright stream sniffer for live .m3u8 stream")

    args = parser.parse_args()
    scraper = LuciferDonghuaScraper()
    storage = scraper.storage

    # 1. Search
    if args.search is not None:
        if not args.search.strip():
            console.print("[yellow]No search query provided.[/yellow]")
            sys.exit(1)
        console.print(f"[cyan]Searching Lucifer Donghua for:[/cyan] [bold]{args.search}[/bold]...")
        try:
            results = scraper.search(args.search)
        except Exception as e:
            console.print(f"[red]Error searching Lucifer Donghua: {e}[/red]")
            sys.exit(1)
        if not results:
            console.print("[red]No results found.[/red]")
            sys.exit(1)

        table = Table(title=f"Search Results for '{args.search}'")
        table.add_column("Title", style="cyan")
        table.add_column("Slug", style="green")
        table.add_column("Type", style="magenta")
        table.add_column("Latest Ep", style="yellow")
        table.add_column("URL", style="dim")

        for r in results:
            table.add_row(r.title, r.slug, r.type, r.latest_episode or "N/A", r.url)
        console.print(table)
        return

    # 2. Donghua Series Info
    if args.info:
        console.print(f"[cyan]Fetching Lucifer Donghua series details for:[/cyan] [bold]{args.info}[/bold]...")
        try:
            detail = scraper.get_donghua_details(args.info)
        except Exception as e:
            console.print(f"[red]Error fetching details: {e}[/red]")
            sys.exit(1)
        if not detail:
            console.print(f"[red]Could not fetch details for: {args.info}[/red]")
            sys.exit(1)

        print_lucifer_donghua_card(detail)

        if detail.episodes:
            ep_table = Table(title=f"Discovered Episodes ({len(detail.episodes)})")
            ep_table.add_column("Ep #", style="green")
            ep_table.add_column("Title", style="cyan")
            ep_table.add_column("Quality", style="magenta")
            ep_table.add_column("Release Date", style="yellow")
            ep_table.add_column("URL", style="dim")

            sample_eps = detail.episodes[:10]
            for ep in sample_eps:
                ep_table.add_row(
                    str(int(ep.episode_number) if ep.episode_number.is_integer() else ep.episode_number),
                    ep.title,
                    ep.quality_tag,
                    ep.release_date or "N/A",
                    ep.url
                )
            if len(detail.episodes) > 10:
                ep_table.add_row("...", "...", "...", "...", "...")
                for ep in detail.episodes[-3:]:
                    ep_table.add_row(
                        str(int(ep.episode_number) if ep.episode_number.is_integer() else ep.episode_number),
                        ep.title,
                        ep.quality_tag,
                        ep.release_date or "N/A",
                        ep.url
                    )

            console.print(ep_table)
        return

    # 3. Episode Details & Mirrors
    if args.episode:
        console.print(f"[cyan]Fetching episode playback details from:[/cyan] {args.episode}...")
        try:
            ep_detail = scraper.get_episode_details(args.episode, resolve_embeds=True, run_sniffer=args.sniff)
        except Exception as e:
            console.print(f"[red]Error resolving episode details: {e}[/red]")
            sys.exit(1)
        if not ep_detail:
            console.print("[red]Could not resolve episode details.[/red]")
            sys.exit(1)

        console.print(Panel(
            f"[bold cyan]Title:[/bold cyan] {ep_detail.episode_title}\n"
            f"[bold cyan]Episode Number:[/bold cyan] {ep_detail.episode_number}\n"
            f"[bold cyan]Views:[/bold cyan] {ep_detail.views or 'N/A'}\n"
            f"[bold cyan]Release Date:[/bold cyan] {ep_detail.release_date or 'N/A'}\n"
            f"[bold cyan]Parent Series:[/bold cyan] {ep_detail.series_title or 'N/A'}\n"
            f"[bold cyan]Prev Episode:[/bold cyan] {ep_detail.prev_episode_url or 'None'}\n"
            f"[bold cyan]Next Episode:[/bold cyan] {ep_detail.next_episode_url or 'None'}",
            title="Episode Info",
            border_style="cyan"
        ))

        if ep_detail.servers:
            server_table = Table(title=f"Streaming Server Mirrors ({len(ep_detail.servers)})")
            server_table.add_column("Server Name", style="green")
            server_table.add_column("Provider", style="magenta")
            server_table.add_column("Quality", style="yellow")
            server_table.add_column("Languages", style="blue")
            server_table.add_column("Embed Iframe URL", style="cyan")

            for s in ep_detail.servers:
                server_table.add_row(
                    s.server_name,
                    s.provider,
                    s.quality,
                    ", ".join(s.languages) if s.languages else "N/A",
                    s.embed_url or s.server_url
                )
            console.print(server_table)

        if ep_detail.downloads:
            dl_table = Table(title=f"Direct Download Links ({len(ep_detail.downloads)})")
            dl_table.add_column("Title", style="magenta")
            dl_table.add_column("Host", style="yellow")
            dl_table.add_column("URL", style="cyan")

            for d in ep_detail.downloads:
                dl_table.add_row(d.title or "Download", d.host, d.url)
            console.print(dl_table)
        return

    # 4. Crawl Series
    if args.crawl:
        console.print(f"[bold green]Starting crawl for Lucifer Donghua series:[/bold green] {args.crawl}")
        result = scraper.crawl_series(args.crawl, scrape_episodes=True, max_episodes=args.max_episodes)
        if result:
            console.print("[bold green]✓ Crawl complete! Saved to SQLite database.[/bold green]")
            print_lucifer_donghua_card(result)
        return

    # 5. Catalog Browse
    if args.catalog:
        console.print(f"[cyan]Browsing catalog (pages: {args.pages})...[/cyan]")
        all_cards = []
        for p in range(1, args.pages + 1):
            cards = scraper.get_catalog_page(p)
            all_cards.extend(cards)

        table = Table(title=f"Catalog Items ({len(all_cards)})")
        table.add_column("Title", style="cyan")
        table.add_column("Slug", style="green")
        table.add_column("Type", style="magenta")
        table.add_column("Latest Ep", style="yellow")

        for c in all_cards:
            table.add_row(c.title, c.slug, c.type, c.latest_episode or "N/A")
        console.print(table)
        return

    # 6. Database Stats
    if args.stats:
        stats = storage.get_stats()
        console.print(Panel(
            f"[bold cyan]Total Donghua Series:[/bold cyan] {stats['total_series']}\n"
            f"[bold cyan]Total Episodes Registered:[/bold cyan] {stats['total_episodes']}\n"
            f"[bold green]Completed Episodes:[/bold green] {stats['completed_episodes']}\n"
            f"[bold yellow]Pending Episodes:[/bold yellow] {stats['pending_episodes']}\n"
            f"[bold red]Failed Episodes:[/bold red] {stats['failed_episodes']}",
            title="Lucifer Donghua SQLite Storage Statistics",
            border_style="magenta"
        ))
        return

    # 7. Retry Failed
    if args.retry_failed:
        count = storage.reset_failed()
        console.print(f"[green]Reset {count} failed episode tasks back to pending state.[/green]")
        return

    # 8. Export to JSON
    if args.export:
        item = storage.get_donghua(args.export)
        if not item:
            console.print(f"[red]Series '{args.export}' not found in database.[/red]")
            return
        out_file = OUTPUT_DIR / f"{args.export}.json"
        out_file.write_text(json.dumps(item.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
        console.print(f"[bold green]✓ Successfully exported to {out_file}[/bold green]")
        return

    parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
