"""Data models for WitDL."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Quality(Enum):
    FHD = "fhd"
    HD = "hd"
    SD = "sd"

    @classmethod
    def from_str(cls, s: str) -> "Quality":
        s = s.lower().strip()
        for q in cls:
            if q.value == s:
                return q
        raise ValueError(f"Unknown quality: {s}")

    @property
    def display(self) -> str:
        return self.value.upper()


class DownloadStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Link:
    """A single download link from a hoster."""
    hoster: str
    url: str
    quality: Quality = Quality.FHD

    def __repr__(self):
        return f"[{self.quality.display}] {self.hoster}: {self.url[:60]}..."


@dataclass
class Episode:
    """An episode with its download links."""
    number: int
    links: list[Link] = field(default_factory=list)
    url: str = ""

    @property
    def best_link(self) -> Optional[Link]:
        """Select the best download link by quality and hoster priority."""
        if not self.links:
            return None

        from .config import load_config
        config = load_config()
        priority = {h: i for i, h in enumerate(config.hoster_priority)}

        def score(link: Link) -> tuple:
            q_score = {Quality.FHD: 3, Quality.HD: 2, Quality.SD: 1}.get(link.quality, 0)
            h_score = priority.get(link.hoster.lower(), 999)
            return (q_score, -h_score)  # higher is better

        return sorted(self.links, key=score, reverse=True)[0]


@dataclass
class Anime:
    """An anime series."""
    name: str
    slug: str
    url: str = ""
    episodes: list[Episode] = field(default_factory=list)

    @property
    def episode_count(self) -> int:
        return len(self.episodes)


@dataclass
class SearchResult:
    """A search result from WitAnime."""
    name: str
    url: str
    anime_type: str = ""
    status: str = ""


@dataclass
class DownloadResult:
    """Result of a download attempt."""
    episode_number: int
    status: DownloadStatus
    filepath: str = ""
    size_bytes: int = 0
    error: str = ""
    hoster_used: str = ""

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)
