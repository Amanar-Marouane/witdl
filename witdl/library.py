"""Library management — track downloads, state, and sessions."""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from .config import DEFAULT_CONFIG_DIR
from .models import DownloadResult, DownloadStatus

STATE_FILE = DEFAULT_CONFIG_DIR / "state.json"


@dataclass
class EpisodeState:
    """State of a single episode download."""
    number: int
    status: str = "pending"
    filepath: str = ""
    size_bytes: int = 0
    hoster: str = ""
    error: str = ""
    attempts: int = 0


@dataclass
class AnimeState:
    """State of an anime's downloads."""
    name: str
    slug: str
    episodes: dict[int, EpisodeState] = field(default_factory=dict)


@dataclass
class AppState:
    """Global application state."""
    anime: dict[str, AnimeState] = field(default_factory=dict)

    def save(self):
        """Save state to disk."""
        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "anime": {
                slug: {
                    "name": a.name,
                    "slug": a.slug,
                    "episodes": {
                        str(num): asdict(ep)
                        for num, ep in a.episodes.items()
                    }
                }
                for slug, a in self.anime.items()
            }
        }
        with open(STATE_FILE, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls) -> "AppState":
        """Load state from disk."""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE) as f:
                    data = json.load(f)
                state = cls()
                for slug, a_data in data.get("anime", {}).items():
                    anime_state = AnimeState(name=a_data["name"], slug=slug)
                    for num_str, ep_data in a_data.get("episodes", {}).items():
                        anime_state.episodes[int(num_str)] = EpisodeState(**ep_data)
                    state.anime[slug] = anime_state
                return state
            except Exception:
                pass
        return cls()


class Library:
    """Manages the local anime library and download state."""

    def __init__(self):
        self.state = AppState.load()

    def save(self):
        self.state.save()

    def get_anime(self, slug: str) -> Optional[AnimeState]:
        return self.state.anime.get(slug)

    def get_or_create_anime(self, name: str, slug: str) -> AnimeState:
        if slug not in self.state.anime:
            self.state.anime[slug] = AnimeState(name=name, slug=slug)
        return self.state.anime[slug]

    def update_episode(self, slug: str, result: DownloadResult):
        """Update episode state from a download result."""
        anime = self.state.anime.get(slug)
        if not anime:
            return
        ep = anime.episodes.get(result.episode_number)
        if not ep:
            ep = EpisodeState(number=result.episode_number)
            anime.episodes[result.episode_number] = ep
        ep.status = result.status.value
        ep.filepath = result.filepath
        ep.size_bytes = result.size_bytes
        ep.hoster = result.hoster_used
        ep.error = result.error
        if result.status == DownloadStatus.FAILED:
            ep.attempts += 1
        self.save()

    def mark_skipped(self, slug: str, episode_num: int, filepath: str, size: int):
        """Mark an episode as skipped (already downloaded)."""
        anime = self.state.anime.get(slug)
        if not anime:
            return
        ep = anime.episodes.get(episode_num)
        if not ep:
            ep = EpisodeState(number=episode_num)
            anime.episodes[episode_num] = ep
        ep.status = "completed"
        ep.filepath = filepath
        ep.size_bytes = size
        self.save()

    def is_downloaded(self, slug: str, episode_num: int) -> bool:
        """Check if an episode is already downloaded."""
        anime = self.state.anime.get(slug)
        if not anime:
            return False
        ep = anime.episodes.get(episode_num)
        if not ep:
            return False
        if ep.status == "completed" and ep.filepath and os.path.exists(ep.filepath):
            return True
        return False

    def get_downloaded_episodes(self, slug: str) -> list[int]:
        """Get list of downloaded episode numbers."""
        anime = self.state.anime.get(slug)
        if not anime:
            return []
        return sorted([
            num for num, ep in anime.episodes.items()
            if ep.status == "completed"
        ])

    def get_missing_episodes(self, slug: str, total: int) -> list[int]:
        """Get list of episode numbers that haven't been downloaded."""
        downloaded = set(self.get_downloaded_episodes(slug))
        return sorted(set(range(1, total + 1)) - downloaded)

    def list_all(self) -> dict[str, dict]:
        """List all anime in library with download counts."""
        result = {}
        for slug, anime in self.state.anime.items():
            downloaded = len([e for e in anime.episodes.values() if e.status == "completed"])
            total = len(anime.episodes)
            failed = len([e for e in anime.episodes.values() if e.status == "failed"])
            result[slug] = {
                "name": anime.name,
                "downloaded": downloaded,
                "total": total,
                "failed": failed,
            }
        return result

    def clean_failed(self):
        """Remove failed download records."""
        for slug, anime in self.state.anime.items():
            to_remove = [
                num for num, ep in anime.episodes.items()
                if ep.status == "failed"
            ]
            for num in to_remove:
                del anime.episodes[num]
        self.save()
