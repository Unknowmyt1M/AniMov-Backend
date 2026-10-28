"""Shared Rich Terminal UI & Aesthetics for AniMov Providers."""

import sys
from typing import Optional, List, Tuple, Any
from contextlib import contextmanager

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich import box

console = Console()

BANNER_ART = r"""
    ___          _ __  ___          
   /   |  ____  (_)  |/  /___  _  __
  / /| | / __ \/ / /|_/ / __ \| |/ /
 / ___ |/ / / / / /  / / /_/ /|   / 
/_/  |_/_/ /_/_/_/  /_/\____/ |_/  
"""


def print_banner(service_name: str, subtitle: str = "High-Speed Anime & Cinema Engine"):
    """Print the signature neon gradient AniMov banner."""
    logo = Text(BANNER_ART, style="bold bright_cyan")
    tagline = Text(f"⚡ {service_name.upper()} ⚡  |  {subtitle}", style="bold bright_yellow")
    panel = Panel(
        Align.center(Text.assemble(logo, "\n", tagline)),
        border_style="bright_magenta",
        box=box.ROUNDED,
        padding=(0, 2),
    )
    console.print(panel)


def format_badge(text: str, bg_color: str = "bright_cyan", fg_color: str = "black") -> str:
    """Format a stylish pill badge."""
    return f"[bold {fg_color} on {bg_color}] {text} [/]"


def format_tags(items: List[str], color: str = "bright_magenta") -> str:
    """Format bullet-separated tags."""
    if not items:
        return "[dim]N/A[/dim]"
    return " • ".join(f"[bold {color}]{it}[/]" for it in items)


def create_table(
    title: str,
    columns: List[Tuple[str, dict]],
    show_lines: bool = True,
    border_style: str = "bright_blue",
    header_style: str = "bold bright_magenta",
) -> Table:
    """Create a standardized beautiful rounded table."""
    table = Table(
        title=title,
        header_style=header_style,
        border_style=border_style,
        box=box.ROUNDED,
        show_lines=show_lines,
    )
    for col_name, col_kwargs in columns:
        table.add_column(col_name, **col_kwargs)
    return table


def print_info_card(
    title: str,
    fields: List[Tuple[str, str, str]],  # (icon + label, value, color)
    synopsis: Optional[str] = None,
    border_style: str = "bright_cyan",
):
    """Render a sleek media information card."""
    lines = []
    for label, val, color in fields:
        if val:
            lines.append(f"[bold bright_white]{label:<18}[/bold bright_white] [{color}]{val}[/{color}]")

    if synopsis:
        lines.append("\n[bold bright_white]📖 Synopsis:[/bold bright_white]")
        lines.append(f"[italic white]{synopsis}[/italic white]")

    card_content = "\n".join(lines)
    panel = Panel(
        card_content.strip(),
        title=f"[bold {border_style}]✦ {title.upper()} ✦[/bold {border_style}]",
        border_style=border_style,
        box=box.ROUNDED,
        padding=(1, 2),
    )
    console.print(panel)


@contextmanager
def status_spinner(message: str, spinner: str = "dots12"):
    """Animated spinner context manager."""
    with console.status(message, spinner=spinner):
        yield
