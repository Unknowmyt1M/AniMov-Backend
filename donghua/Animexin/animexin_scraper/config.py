"""Configuration loading and defaults.

Precedence (lowest -> highest):
  1. code defaults
  2. config.json file (CLI --config or ./config.json)
  3. environment variables (ANIMEXIN_*)
  4. CLI arguments
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Optional

DEFAULT_DOMAINS = [
    "https://animexin.dev",
    "https://animexin.vip",
    "https://animexin.xyz",
]
DEFAULT_SOURCE = DEFAULT_DOMAINS[0] + "/"


@dataclass
class Config:
    source: str = DEFAULT_SOURCE
    mirror_domains: list = field(default_factory=lambda: list(DEFAULT_DOMAINS))

    max_anime: Optional[int] = None
    max_episodes_per_anime: Optional[int] = None
    max_servers_per_episode: Optional[int] = None
    title_filter: Optional[str] = None
    search_query: Optional[str] = None
    detail_url: Optional[str] = None

    full: bool = False
    resume: bool = True
    refresh: bool = False
    reset: bool = False
    retry_failed: bool = False
    validate_only: bool = False
    export: bool = True

    concurrency: int = 6
    request_delay: float = 0.0
    timeout: float = 45.0
    retries: int = 3
    backoff_base: float = 2.0
    max_backoff: float = 60.0

    db_path: str = "animexin.db"
    output_dir: str = "output"
    html_cache_dir: str = "cache"
    cache_enabled: bool = True

    use_browser_fallback: bool = True
    headless: bool = True
    browser_wait_ms: int = 5000

    log_level: str = "INFO"
    log_file: Optional[str] = None

    discover_embeds: bool = True

    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    _config_path: Optional[str] = field(default=None, repr=False)

    def resolve_paths(self) -> None:
        self.source = self.source.rstrip("/") + "/"
        base = Path.cwd()
        for attr in ("db_path", "output_dir", "html_cache_dir"):
            val = getattr(self, attr)
            if val and not Path(val).is_absolute():
                setattr(self, attr, str(base / val))

    @classmethod
    def from_file(cls, path: str | Path) -> dict:
        p = Path(path)
        if not p.is_file():
            return {}
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return {k: v for k, v in data.items() if k in {f.name for f in fields(cls)}}

    @classmethod
    def from_env(cls) -> dict:
        out = {}
        for f in fields(cls):
            key = "ANIMEXIN_" + f.name.upper()
            if key in os.environ:
                raw = os.environ[key]
                if f.name in ("concurrency", "retries", "max_anime", "max_episodes_per_anime",
                              "max_servers_per_episode", "browser_wait_ms"):
                    out[f.name] = int(raw) if raw.strip() else None
                elif f.name in ("request_delay", "timeout", "backoff_base", "max_backoff"):
                    out[f.name] = float(raw) if raw.strip() else None
                elif f.name in ("full", "resume", "refresh", "reset", "retry_failed",
                                "validate_only", "export", "cache_enabled",
                                "use_browser_fallback", "headless", "discover_embeds"):
                    out[f.name] = raw.strip().lower() in ("1", "true", "yes", "on")
                elif f.name == "mirror_domains":
                    out[f.name] = [x.strip() for x in raw.split(",") if x.strip()]
                else:
                    out[f.name] = raw
        return out

    def merge(self, data: dict) -> None:
        for k, v in data.items():
            if hasattr(self, k) and v is not None:
                setattr(self, k, v)

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self) if not f.name.startswith("_")}

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        cfg = cls()
        if config_path:
            cfg.merge(cls.from_file(config_path))
        else:
            if Path("config.json").is_file():
                cfg.merge(cls.from_file("config.json"))
        cfg.merge(cls.from_env())
        cfg.resolve_paths()
        return cfg
