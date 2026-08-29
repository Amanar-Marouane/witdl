"""Configuration management for WitDL."""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

DEFAULT_CONFIG_DIR = Path.home() / ".witdl"
CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"


@dataclass
class Config:
    """WitDL configuration."""
    download_dir: str = str(Path.home() / "anime")
    quality: str = "fhd"
    hoster_priority: list[str] = field(default_factory=lambda: [
        "mediafire", "hexload", "mp4upload", "gofile", "workupload", "wahmi"
    ])
    max_concurrent_downloads: int = 2
    delay_between_episodes: float = 2.0
    timeout_per_download: int = 900
    auto_retry: bool = True
    max_retries: int = 3
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

    def save(self):
        """Save config to disk."""
        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls) -> "Config":
        """Load config from disk, or return defaults."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    data = json.load(f)
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except Exception:
                pass
        return cls()


def load_config() -> Config:
    """Convenience function to load config."""
    return Config.load()
