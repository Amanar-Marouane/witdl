"""Mediafire resolver — extract direct download URL."""

import re
from .base import BaseResolver


class MediafireResolver(BaseResolver):
    """Resolves mediafire URLs to direct download links."""

    def resolve(self, url: str) -> str | None:
        try:
            html = self._fetch(url)
            m = re.search(r'href="(https?://download\d+\.mediafire\.com/[^"]+)"', html)
            if m:
                return m.group(1)
        except Exception:
            pass
        return None
