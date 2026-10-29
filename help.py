#!/usr/bin/env python3
"""AniMov Backend — Interactive CLI User Manual & Command Guide.

Run this script to view command syntax, practical examples, architecture details,
and provider capabilities across Movies, Anime, Donghua, and Stream Extractors.

Usage:
    python help.py                 # Full Interactive Overview & Quickstart
    python help.py movies          # Movies & Web Series Scrapers
    python help.py anime           # Anime Scrapers & Streaming Engines
    python help.py donghua         # Chinese Animation (Donghua) Engines
    python help.py extractors      # Video Host Unpackers & M3U8 Stream Extractors
    python help.py --all           # Print complete comprehensive documentation
"""

import sys
import argparse
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich.markdown import Markdown

from common.ui import (
    console,
    print_banner,
    create_table,
    box,
)


def print_quickstart():
    """Print the general AniMov execution rules and environment tips."""
    content = """[bold bright_cyan]✦ Welcome to AniMov Backend CLI Suite ✦[/bold bright_cyan]

AniMov Backend is a unified high-performance scraping, streaming, and metadata engine for:
  • [bold yellow]Bollywood, Hollywood & Dual Audio Cinema[/bold yellow] (BollyFlix, HDHub4u, MoviesMod, HindiLinks4u, KMMovies, 1Tube)
  • [bold magenta]Japanese Anime[/bold magenta] (AniKage, AniKoto, AnimeSalt, WatchAnimeWorld, AnimeSuge, Miruro)
  • [bold green]Chinese Donghua[/bold green] (AnimeCube, AnimeKhor, DonghuaStream, LuciferDonghua, ToonStream)
  • [bold cyan]HLS / M3U8 Stream Extractors[/bold cyan] (yt-dlp, Rumble, Dailymotion, HubCloud, Streamtape, Dood, SpeedoStream)

[bold bright_white]⚡ Key CLI Execution Rules (Windows / PowerShell):[/bold bright_white]
  1. Always run commands from the project root: [bold green]E:\\Projects\\Automation\\AniMov Backend[/bold green]
  2. Use module execution syntax: [bold bright_yellow]python -m <category>.<provider>.cli <options>[/bold bright_yellow]
  3. If your query has spaces or special characters, always wrap it in quotes: [dim]"Iron Man"[/dim]
  4. Most search tables fold long Slugs and URLs cleanly without truncating, making it easy to copy exact slugs!
  5. Built-in [bold bright_cyan]Google DNS-over-HTTPS (DoH)[/bold bright_cyan] automatically bypasses ISP blocks for restricted domains.
"""
    console.print(
        Panel(
            content.strip(),
            title="[bold bright_magenta]🚀 QUICKSTART GUIDE[/bold bright_magenta]",
            border_style="bright_magenta",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def show_movies_guide():
    """Detailed guide for all cinema and web series scrapers."""
    console.print("\n[bold bright_yellow]══════════════════════ 🎬 MOVIES & WEB SERIES SCRAPERS ══════════════════════[/bold bright_yellow]\n")

    table = create_table(
        title="✨ Movies & Series Providers Matrix ✨",
        columns=[
            ("Provider", {"style": "bold bright_cyan", "width": 14}),
            ("Specialty / Content", {"style": "bright_white", "width": 32}),
            ("Search Command", {"style": "bright_yellow", "overflow": "fold"}),
            ("Detail / Download Links Command", {"style": "bright_green", "overflow": "fold"}),
        ],
        border_style="bright_yellow",
        header_style="bold bright_yellow",
    )

    table.add_row(
        "BollyFlix",
        "Dual Audio Hollywood, Bollywood, Series (fxlinks & linksmod)",
        'python -m movies.bollyflix.cli --search "Iron Man"',
        'python -m movies.bollyflix.cli --detail "iron-man-2008-dual-audio-hindi-english-movie"',
    )
    table.add_row(
        "HDHub4u",
        "4K 2160p, 1080p, 720p Dual Audio, HubDrive & HubCloud",
        'python -m movies.hdhub4u.cli search "Iron Man"',
        'python -m movies.hdhub4u.cli detail "iron-man-2008-hindi-bluray"',
    )
    table.add_row(
        "MoviesMod",
        "ModPro archives, Dual Audio 480p-1080p, DoH bypass",
        'python -m movies.moviesmod.cli --search "Batman"',
        'python -m movies.moviesmod.cli --detail "download-the-batman-the-long-halloween-deluxe-edition-2022-english-480p-720p-1080p"',
    )
    table.add_row(
        "HindiLinks4u",
        "Hindi Movies Streaming (Streamtape, Dood, MixDrop)",
        'python -m movies.hindilinks4u.cli --search "Sholay"',
        'python -m movies.hindilinks4u.cli --detail "sholay-1975"',
    )
    table.add_row(
        "KMMovies",
        "South Hindi Dubbed, Bollywood, MagicLinks downloads",
        'python -m movies.kmmovies.cli --search "Avatar"',
        'python -m movies.kmmovies.cli --detail "mahavatar-narsimha-2025-hindi-download-1080p-web-dl"',
    )
    table.add_row(
        "1Tube",
        "TMDB-indexed streaming mirrors (Layla, VidSrc, 2Embed)",
        'python -m movies.onetube.cli --search "Avengers"',
        'python -m movies.onetube.cli --detail 299534',
    )
    console.print(table)

    examples = """[bold bright_cyan]💡 Practical Usage Examples for Movies:[/bold bright_cyan]

[bold yellow]# 1. Search for a movie or TV series on BollyFlix:[/bold yellow]
python -m movies.bollyflix.cli --search "Stranger Things"

[bold yellow]# 2. Extract direct download gateway links from BollyFlix (auto-resolves active domain):[/bold yellow]
python -m movies.bollyflix.cli --detail "stranger-things-season-4-dual-audio-hindi-english-web-series"

[bold yellow]# 3. Search HDHub4u with page navigation:[/bold yellow]
python -m movies.hdhub4u.cli search "Oppenheimer" --page 1

[bold yellow]# 4. Browse HDHub4u Bollywood or Hollywood catalog:[/bold yellow]
python -m movies.hdhub4u.cli catalog --category bollywood-movies
python -m movies.hdhub4u.cli catalog --category hollywood-movies

[bold yellow]# 5. Search MoviesMod with DoH enabled (bypasses ISP blocks):[/bold yellow]
python -m movies.moviesmod.cli --search "Deadpool"

[bold yellow]# 6. Stream mirrors from 1Tube by TMDB ID:[/bold yellow]
python -m movies.onetube.cli --detail 299536
"""
    console.print(Panel(examples.strip(), border_style="cyan", box=box.ROUNDED, padding=(1, 2)))


def show_anime_guide():
    """Detailed guide for all Anime scrapers."""
    console.print("\n[bold bright_magenta]══════════════════════ ⛩️ JAPANESE ANIME SCRAPERS ══════════════════════[/bold bright_magenta]\n")

    table = create_table(
        title="✨ Anime Providers Matrix ✨",
        columns=[
            ("Provider", {"style": "bold bright_magenta", "width": 16}),
            ("Features / Highlights", {"style": "bright_white", "width": 30}),
            ("Search Command", {"style": "bright_yellow", "overflow": "fold"}),
            ("Playback / Episode Command", {"style": "bright_green", "overflow": "fold"}),
        ],
        border_style="bright_magenta",
        header_style="bold bright_magenta",
    )

    table.add_row(
        "AniKage",
        "AniList sync, Sub & Dub servers, score & genres",
        'python -m anime.anikage.cli search "Bleach"',
        'python -m anime.anikage.cli detail "<slug>"',
    )
    table.add_row(
        "AniKoto",
        "Comprehensive episode rosters, Sub/Dub breakdown",
        'python -m anime.anikoto.cli --search "Naruto"',
        'python -m anime.anikoto.cli --episode "naruto-eybxz" --ep 1',
    )
    table.add_row(
        "AnimeSalt",
        "Multi-language dubs, fast stream sources",
        'python -m anime.animesalt.cli --search "Solo Leveling"',
        'python -m anime.animesalt.cli --detail "solo-leveling"',
    )
    table.add_row(
        "WatchAnimeWorld",
        "India Regional Anime Dubs (Hindi, Tamil, Telugu)",
        'python -m anime.watchanimeworld.cli --search "One Piece"',
        'python -m anime.watchanimeworld.cli --detail "one-piece"',
    )
    table.add_row(
        "AnimeSuge",
        "Fast Anime Streaming, Sub & Dub servers, batch crawling",
        'python -m anime.animesuge.cli --search "Bleach"',
        'python -m anime.animesuge.cli --episode "bleach-yaa9n" --ep 1',
    )
    table.add_row(
        "Miruro",
        "GraphQL API, high-res posters, format & score metrics",
        'python -m anime.miruro.cli --search "Bleach"',
        'python -m anime.miruro.cli --episode "_xmqpElBfc0TJw5QvjhmLekg22_fLvcv" --ep 1',
    )
    table.add_row(
        "ReAnime",
        "Fast streaming API, season metadata & episode lists",
        'python -m anime.reanime.cli --search "Bleach"',
        'python -m anime.reanime.cli --episode "bleach-p76y5k" --ep 1',
    )
    console.print(table)

    examples = """[bold bright_cyan]💡 Practical Usage Examples for Anime:[/bold bright_cyan]

[bold yellow]# 1. Search AniKoto for all Naruto seasons & movies:[/bold yellow]
python -m anime.anikoto.cli --search "Naruto"

[bold yellow]# 2. Inspect episodes and server streams on AniKoto:[/bold yellow]
python -m anime.anikoto.cli --detail "naruto-eybxz"
python -m anime.anikoto.cli --episode "naruto-eybxz" --ep 500

[bold yellow]# 3. Search & stream on AnimeSuge:[/bold yellow]
python -m anime.animesuge.cli --search "Bleach"
python -m anime.animesuge.cli --episode "bleach-yaa9n" --ep 1

[bold yellow]# 4. Search & stream on Miruro (GraphQL):[/bold yellow]
python -m anime.miruro.cli --search "Attack on Titan"
python -m anime.miruro.cli --info "_xmqpElBfc0TJw5QvjhmLekg22_fLvcv"

[bold yellow]# 5. Search Hindi dubbed anime on WatchAnimeWorld:[/bold yellow]
python -m anime.watchanimeworld.cli --search "Jujutsu Kaisen"

[bold yellow]# 6. Search multi-audio dubs on AnimeSalt:[/bold yellow]
python -m anime.animesalt.cli --search "Demon Slayer"
"""
    console.print(Panel(examples.strip(), border_style="magenta", box=box.ROUNDED, padding=(1, 2)))


def show_donghua_guide():
    """Detailed guide for Chinese Animation (Donghua) scrapers."""
    console.print("\n[bold bright_green]══════════════════════ 🐉 CHINESE DONGHUA SCRAPERS ══════════════════════[/bold bright_green]\n")

    table = create_table(
        title="✨ Donghua Providers Matrix ✨",
        columns=[
            ("Provider", {"style": "bold bright_green", "width": 16}),
            ("Features / Highlights", {"style": "bright_white", "width": 30}),
            ("Search Command", {"style": "bright_yellow", "overflow": "fold"}),
            ("Detail / Stream Command", {"style": "bright_cyan", "overflow": "fold"}),
        ],
        border_style="bright_green",
        header_style="bold bright_green",
    )

    table.add_row(
        "AnimeCube",
        "Next.js scraper, direct M3U8 sniffer via Playwright",
        'python -m donghua.AnimeCube.cli --search "Soul Land"',
        'python -m donghua.AnimeCube.cli --info "soul-land-2-the-peerless-tang-clan"',
    )
    table.add_row(
        "AnimeKhor",
        "High quality donghua, ONA & movie streams",
        'python -m donghua.AnimeKhor.cli --search "Renegade"',
        'python -m donghua.AnimeKhor.cli --info "renegade-immortal"',
    )
    table.add_row(
        "DonghuaStream",
        "Ongoing Chinese series, fast direct stream links",
        'python -m donghua.DonghuaStream.cli --search "Soul Land"',
        'python -m donghua.DonghuaStream.cli --info "soul-land-2nd"',
    )
    table.add_row(
        "LuciferDonghua",
        "Character roster, high-res posters, stream mirrors",
        'python -m donghua.Luciferdonghua.cli --search "Perfect World"',
        'python -m donghua.Luciferdonghua.cli --info "perfect-world-new"',
    )
    table.add_row(
        "ToonStream",
        "Cartoons & Donghua series catalog with ratings",
        'python -m donghua.toonstream.cli search "Ben 10"',
        'python -m donghua.toonstream.cli detail "ben-10-alien-force"',
    )
    table.add_row(
        "AnimeXin",
        "Catalog crawler, batch pipeline, SQLite caching",
        'python -m donghua.Animexin.cli --search "Martial Master"',
        'python -m donghua.Animexin.cli --url "https://animexin.dev/anime/<slug>/"',
    )
    console.print(table)

    examples = """[bold bright_cyan]💡 Practical Usage Examples for Donghua:[/bold bright_cyan]

[bold yellow]# 1. Search for Renegade Immortal on AnimeKhor:[/bold yellow]
python -m donghua.AnimeKhor.cli --search "Renegade Immortal"

[bold yellow]# 2. Fetch full series details and episodes from LuciferDonghua:[/bold yellow]
python -m donghua.Luciferdonghua.cli --info "perfect-world-new"

[bold yellow]# 3. Sniff direct stream URL from AnimeCube using Playwright headless engine:[/bold yellow]
python -m donghua.AnimeCube.cli --episode "soul-land-2-the-peerless-tang-clan" --ep 1 --sniff
"""
    console.print(Panel(examples.strip(), border_style="green", box=box.ROUNDED, padding=(1, 2)))


def show_extractors_guide():
    """Guide for Stream Extractors, yt-dlp, and video host unpackers."""
    console.print("\n[bold bright_cyan]══════════════════════ ⚡ STREAM EXTRACTORS & UNPACKERS ══════════════════════[/bold bright_cyan]\n")

    content = """[bold bright_white]How AniMov Extracts Direct HLS / M3U8 Streams from Video Hosts:[/bold bright_white]

1. [bold yellow]Dailymotion / Rumble URL Normalization:[/bold yellow]
   Iframe embed URLs are normalized to canonical playable URLs:
   • [dim]https://geo.dailymotion.com/player/xhojl.html?video=k4wD3bgoXxbXrVM5AaC[/dim]
     ➜ [bold green]https://www.dailymotion.com/video/k4wD3bgoXxbXrVM5AaC[/bold green]
   
   Then [bold cyan]yt-dlp[/bold cyan] directly dumps the master `.m3u8` manifest and video resolution formats:
   [bold bright_yellow]yt-dlp -g -f "best" "https://www.dailymotion.com/video/k4wD3bgoXxbXrVM5AaC"[/bold bright_yellow]

2. [bold yellow]Third-Party Video Hosts Unpackers:[/bold yellow]
   AniMov includes unpacking logic for major third-party streaming hosts:
   • [bold bright_cyan]Streamtape[/bold bright_cyan]: Decodes obfuscated token in HTML script tag (`document.getElementById('videolink').innerHTML`).
   • [bold bright_cyan]DoodStream[/bold bright_cyan]: Resolves `/pass_md5/` token and appends random timestamp salt to build direct MP4 link.
   • [bold bright_cyan]HubCloud / HubDrive / HubCDN[/bold bright_cyan]: Automates gateway countdowns and extracts final direct cloud download links.
   • [bold bright_cyan]MixDrop[/bold bright_cyan]: Unpacks JavaScript `eval(function(p,a,c,k,e,d)...)` packing to retrieve the MP4 file URL.

3. [bold yellow]Quick yt-dlp Command Cheatsheet:[/bold yellow]
   • [bold green]Get raw HLS / M3U8 link:[/bold green]  `yt-dlp -g "<playable_url>"`
   • [bold green]List available qualities:[/bold green] `yt-dlp -F "<playable_url>"`
   • [bold green]Stream via mpv / VLC:[/bold green]      `yt-dlp -o - "<playable_url>" | mpv -`
"""
    console.print(Panel(content.strip(), title="[bold bright_cyan]⚡ UNPACKER ARCHITECTURE[/bold bright_cyan]", border_style="bright_cyan", box=box.ROUNDED, padding=(1, 2)))


def main():
    """Main CLI entrypoint for help.py manual."""
    parser = argparse.ArgumentParser(
        description="AniMov Backend Interactive Manual & Command Guide",
        epilog="Example: python help.py movies",
    )
    parser.add_argument(
        "topic",
        nargs="?",
        choices=["movies", "cinema", "anime", "donghua", "extractors", "unpackers"],
        help="Category manual to inspect",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Print complete guide for all categories",
    )

    args = parser.parse_args()

    print_banner("AniMov Manual", "Unified CLI Handbook & Examples")

    if args.all:
        print_quickstart()
        show_movies_guide()
        show_anime_guide()
        show_donghua_guide()
        show_extractors_guide()
        return

    topic = (args.topic or "").lower()

    if topic in ("movies", "cinema"):
        show_movies_guide()
    elif topic == "anime":
        show_anime_guide()
    elif topic == "donghua":
        show_donghua_guide()
    elif topic in ("extractors", "unpackers"):
        show_extractors_guide()
    else:
        # Default overview
        print_quickstart()
        show_movies_guide()
        console.print(
            "\n[bold bright_white]💡 Want to view other sections?[/bold bright_white]\n"
            "  • [cyan]python help.py anime[/cyan]       (Anime scrapers & episode commands)\n"
            "  • [green]python help.py donghua[/green]     (Chinese Donghua scrapers)\n"
            "  • [yellow]python help.py extractors[/yellow]  (M3U8 extractors & host unpackers)\n"
            "  • [magenta]python help.py --all[/magenta]       (Complete manual with everything)\n"
        )


if __name__ == "__main__":
    main()
