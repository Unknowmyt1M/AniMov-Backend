"""
CLI Interface for Lucifer Donghua Scraper.
Supports searching, viewing show metadata, character lists,
inspecting mirror video players, and full series crawling.
"""

import argparse
import json
import sys
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
    from .scraper import LuciferDonghuaScraper
    from .storage import LuciferStorage
    from .config import OUTPUT_DIR
except ImportError:
    from donghua.Luciferdonghua.scraper import LuciferDonghuaScraper
    from donghua.Luciferdonghua.storage import LuciferStorage
    from donghua.Luciferdonghua.config import OUTPUT_DIR


def print_lucifer_donghua_card(donghua):
    """Renders formatted panel with Lucifer Donghua metadata."""
    characters_str = ", ".join([f"{c.name} ({c.role})" for c in donghua.characters[:5]]) if donghua.characters else "[dim]N/A[/dim]"
    producers_str = ", ".join(donghua.producers) if donghua.producers else "[dim]N/A[/dim]"
    genres_str = " • ".join(f"[bold bright_magenta]{g}[/]" for g in donghua.genres) if donghua.genres else "[dim]N/A[/dim]"
    rating_str = f"⭐ [bold bright_yellow]{donghua.rating}[/bold bright_yellow]" if donghua.rating else "[dim]N/A[/dim]"

    meta_info = f"""[bold bright_white]🎬 Title:[/bold bright_white]          [bold bright_yellow]{donghua.title}[/bold bright_yellow]
[bold bright_white]🇨🇳 Alt Titles:[/bold bright_white]     [white]{donghua.alternative_titles or 'N/A'}[/white]
[bold bright_white]📡 Status:[/bold bright_white]         [bright_blue]{donghua.status or 'N/A'}[/bright_blue]
[bold bright_white]⭐ Rating:[/bold bright_white]         {rating_str}
[bold bright_white]📺 Type:[/bold bright_white]           [bold on dark_blue] {donghua.type} [/]
[bold bright_white]🏢 Studio:[/bold bright_white]         [bright_green]{donghua.studio or 'N/A'}[/bright_green]
[bold bright_white]🎬 Director:[/bold bright_white]       [bright_cyan]{donghua.director or 'N/A'}[/bright_cyan]
[bold bright_white]👥 Producers:[/bold bright_white]      [dim]{producers_str}[/dim]
[bold bright_white]📅 Released Year:[/bold bright_white]  [bright_green]{donghua.released_year or 'N/A'}[/bright_green]
[bold bright_white]⏱️  Duration:[/bold bright_white]       [bright_yellow]{donghua.duration or 'N/A'}[/bright_yellow]
[bold bright_white]🎞️  Expected Eps:[/bold bright_white]   [bold bright_cyan]{donghua.total_episodes_expected or 'N/A'}[/bold bright_cyan] (Scraped: [bold green]{donghua.total_scraped_episodes}[/bold green])
[bold bright_white]🎭 Genres:[/bold bright_white]         {genres_str}
[bold bright_white]👥 Characters:[/bold bright_white]     [dim]{characters_str}[/dim]

[bold bright_white]📖 Synopsis:[/bold bright_white]
[italic white]{donghua.synopsis.strip() if donghua.synopsis else 'N/A'}[/italic white]
"""
    console.print(
        Panel(
            meta_info.strip(),
            title=f"[bold bright_cyan]✦ {donghua.title.upper()} ✦[/bold bright_cyan]",
            border_style="bright_cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def main():
    parser = argparse.ArgumentParser(description="Lucifer Donghua Production Scraper CLI")
    parser.add_argument("--search", type=str, nargs="?", const="", default=None, help="Search for Donghua by query")
    parser.add_argument("--info", type=str, help="Get series metadata and episode table by slug or URL")
    parser.add_argument("--all", "-a", action="store_true", help="Show all episodes without truncating")
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

    print_banner("Lucifer Donghua", "Donghua Series, Character Roster & Streaming Mirrors")

    try:
        # 1. Search
        if args.search is not None:
            if not args.search.strip():
                console.print("[yellow]⚠️  No search query provided.[/yellow]")
                sys.exit(1)
            with status_spinner(f"Searching Lucifer Donghua for '{args.search}'..."):
                results = scraper.search(args.search)
            if not results:
                console.print("\n[yellow]⚠️  No results found.[/yellow]\n")
                sys.exit(1)

            table = create_table(
                title=f"✨ Search Results for '{args.search}' ({len(results)}) ✨",
                columns=[
                    ("Title", {"style": "bold bright_white"}),
                    ("Slug", {"style": "bright_green"}),
                    ("Type", {"style": "bright_magenta", "justify": "center"}),
                    ("Latest Ep", {"style": "bright_yellow", "justify": "center"}),
                    ("URL", {"style": "underline cyan"}),
                ],
                border_style="bright_blue",
                header_style="bold bright_magenta",
            )

            for r in results:
                table.add_row(r.title, r.slug, r.type, r.latest_episode or "N/A", r.url)
            console.print(table)
            return

        # 2. Donghua Series Info
        if args.info:
            with status_spinner(f"Fetching Lucifer Donghua series details for '{args.info}'..."):
                detail = scraper.get_donghua_details(args.info)
            if not detail:
                console.print(f"[red]❌ Could not fetch details for: {args.info}[/red]")
                sys.exit(1)

            print_lucifer_donghua_card(detail)

            if detail.episodes:
                show_all = args.all
                ep_limit = 50 if not show_all else len(detail.episodes)
                ep_list = detail.episodes if show_all else detail.episodes[:ep_limit]

                ep_table = create_table(
                    title=f"📺 Discovered Episodes ({len(detail.episodes)} Total{' - Showing First ' + str(ep_limit) if not show_all and len(detail.episodes) > ep_limit else ''})",
                    columns=[
                        ("Ep #", {"style": "bold bright_yellow", "justify": "center", "width": 8}),
                        ("Title", {"style": "bold bright_white"}),
                        ("Quality", {"style": "bright_green", "justify": "center"}),
                        ("Release Date", {"style": "dim white", "justify": "center"}),
                        ("URL", {"style": "underline cyan"}),
                    ],
                    border_style="cyan",
                    header_style="bold bright_cyan",
                )

                for ep in ep_list:
                    ep_num_str = str(int(ep.episode_number) if ep.episode_number.is_integer() else ep.episode_number)
                    ep_table.add_row(
                        ep_num_str,
                        ep.title or f"Episode {ep_num_str}",
                        ep.quality_tag,
                        ep.release_date or "N/A",
                        ep.url,
                    )

                if not show_all and len(detail.episodes) > ep_limit:
                    remaining = len(detail.episodes) - ep_limit
                    ep_table.add_row("...", f"[dim italic]+ {remaining} more episodes (use --all to show all)[/dim italic]", "...", "...", "...")

                console.print(ep_table)
            return

        # 3. Episode Details & Mirrors
        if args.episode:
            with status_spinner(f"Fetching episode playback details from '{args.episode}'..."):
                ep_detail = scraper.get_episode_details(args.episode, resolve_embeds=True, run_sniffer=args.sniff)
            if not ep_detail:
                console.print("[red]❌ Could not resolve episode details.[/red]")
                sys.exit(1)

            panel_content = f"""[bold bright_white]🎬 Title:[/bold bright_white]          [bold bright_yellow]{ep_detail.episode_title}[/bold bright_yellow]
[bold bright_white]🔢 Episode Number:[/bold bright_white] [bold bright_cyan]{ep_detail.episode_number}[/bold bright_cyan]
[bold bright_white]👁️  Views:[/bold bright_white]          [bright_green]{ep_detail.views or 'N/A'}[/bright_green]
[bold bright_white]📅 Release Date:[/bold bright_white]   [dim]{ep_detail.release_date or 'N/A'}[/dim]
[bold bright_white]📚 Parent Series:[/bold bright_white]  [white]{ep_detail.series_title or 'N/A'}[/white]
[bold bright_white]⏪ Prev Episode:[/bold bright_white]   [dim]{ep_detail.prev_episode_url or 'None'}[/dim]
[bold bright_white]⏩ Next Episode:[/bold bright_white]   [dim]{ep_detail.next_episode_url or 'None'}[/dim]
"""
            console.print(
                Panel(
                    panel_content.strip(),
                    title=f"[bold bright_green]✦ Episode Playback: Episode {ep_detail.episode_number} ✦[/bold bright_green]",
                    border_style="bright_green",
                    box=box.ROUNDED,
                    padding=(1, 2),
                )
            )

            if ep_detail.servers:
                server_table = create_table(
                    title=f"🖥️  Streaming Server Mirrors ({len(ep_detail.servers)})",
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

                for s in ep_detail.servers:
                    server_table.add_row(
                        s.server_name,
                        s.provider,
                        s.quality,
                        ", ".join(s.languages) if s.languages else "N/A",
                        s.embed_url or s.server_url,
                    )
                console.print(server_table)

            if ep_detail.downloads:
                dl_table = create_table(
                    title=f"⬇️  Direct Download Links ({len(ep_detail.downloads)})",
                    columns=[
                        ("Title", {"style": "bold bright_white"}),
                        ("Host", {"style": "bright_yellow", "justify": "center"}),
                        ("Download URL", {"style": "underline dim"}),
                    ],
                    border_style="bright_yellow",
                    header_style="bold bright_yellow",
                )

                for d in ep_detail.downloads:
                    dl_table.add_row(d.title or "Download", d.host, d.url)
                console.print(dl_table)
            return

        # 4. Crawl Series
        if args.crawl:
            with status_spinner(f"Crawling Lucifer Donghua series '{args.crawl}'..."):
                result = scraper.crawl_series(args.crawl, scrape_episodes=True, max_episodes=args.max_episodes)
            if result:
                console.print("[bold bright_green]✓ Crawl complete! Saved to SQLite database.[/bold bright_green]")
                print_lucifer_donghua_card(result)
            return

        # 5. Catalog Browse
        if args.catalog:
            with status_spinner(f"Browsing catalog (pages: {args.pages})..."):
                all_cards = []
                for p in range(1, args.pages + 1):
                    cards = scraper.get_catalog_page(p)
                    all_cards.extend(cards)

            table = create_table(
                title=f"✨ Catalog Items ({len(all_cards)}) ✨",
                columns=[
                    ("Title", {"style": "bold bright_white"}),
                    ("Slug", {"style": "bright_green"}),
                    ("Type", {"style": "bright_magenta", "justify": "center"}),
                    ("Latest Ep", {"style": "bright_yellow", "justify": "center"}),
                ],
                border_style="bright_blue",
                header_style="bold bright_magenta",
            )

            for c in all_cards:
                table.add_row(c.title, c.slug, c.type, c.latest_episode or "N/A")
            console.print(table)
            return

        # 6. Database Stats
        if args.stats:
            stats = storage.get_stats()
            content = f"""[bold bright_white]📚 Total Donghua Series:[/bold bright_white]     [bold cyan]{stats['total_series']}[/bold cyan]
[bold bright_white]📺 Total Episodes Registered:[/bold bright_white] [bold yellow]{stats['total_episodes']}[/bold yellow]
[bold bright_white]✓ Completed Episodes:[/bold bright_white]         [bold green]{stats['completed_episodes']}[/bold green]
[bold bright_white]⏳ Pending Episodes:[/bold bright_white]           [bright_yellow]{stats['pending_episodes']}[/bright_yellow]
[bold bright_white]❌ Failed Episodes:[/bold bright_white]            [bold red]{stats['failed_episodes']}[/bold red]
"""
            console.print(
                Panel(
                    content.strip(),
                    title="[bold bright_magenta]✦ Lucifer Donghua SQLite Storage Statistics ✦[/bold bright_magenta]",
                    border_style="bright_magenta",
                    box=box.ROUNDED,
                    padding=(1, 2),
                )
            )
            return

        # 7. Retry Failed
        if args.retry_failed:
            count = storage.reset_failed()
            console.print(f"[green]✓ Reset {count} failed episode tasks back to pending state.[/green]")
            return

        # 8. Export to JSON
        if args.export:
            item = storage.get_donghua(args.export)
            if not item:
                console.print(f"[red]❌ Series '{args.export}' not found in database.[/red]")
                return
            out_file = OUTPUT_DIR / f"{args.export}.json"
            out_file.write_text(json.dumps(item.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
            console.print(f"[bold bright_green]✓ Successfully exported to {out_file}[/bold bright_green]")
            return

        parser.print_help()

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
