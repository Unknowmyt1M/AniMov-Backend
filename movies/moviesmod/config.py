"""Configuration for MoviesMod Scraper."""

from pydantic import BaseModel, Field

class MoviesmodConfig(BaseModel):
    """Configuration settings."""
    base_url: str = Field(default="https://moviesmod.meme")
    timeout_seconds: int = Field(default=15)
    max_retries: int = Field(default=3)
    backoff_factor: float = Field(default=1.5)
    db_path: str = Field(default="data/moviesmod.db")
    cache_ttl_hours: int = Field(default=24)
    impersonate_profile: str = Field(default="chrome124")

    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

config = MoviesmodConfig()
