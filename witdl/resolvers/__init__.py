"""Hoster resolvers — extract direct download URLs."""

from .base import BaseResolver
from .mediafire import MediafireResolver
from .hexload import HexloadResolver
from .mp4upload import Mp4uploadResolver
from .gofile import GofileResolver

# Registry of all resolvers
RESOLVERS: dict[str, BaseResolver] = {
    "mediafire": MediafireResolver(),
    "hexload": HexloadResolver(),
    "mp4upload": Mp4uploadResolver(),
    "gofile": GofileResolver(),
}


def get_resolver(hoster: str) -> BaseResolver | None:
    """Get a resolver by hoster name."""
    return RESOLVERS.get(hoster.lower())


def resolve_url(hoster: str, url: str) -> str | None:
    """Resolve a hoster URL to a direct download URL."""
    resolver = get_resolver(hoster)
    if resolver:
        return resolver.resolve(url)
    return None
