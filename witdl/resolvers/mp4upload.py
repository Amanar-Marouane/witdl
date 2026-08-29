"""Mp4upload resolver — extract direct video URL from embed page."""

import re
from .base import BaseResolver


class Mp4uploadResolver(BaseResolver):
    """Resolves mp4upload URLs to direct video links via their embed page."""

    def resolve(self, url: str) -> str | None:
        try:
            m = re.search(r'mp4upload\.com/(\w+)', url)
            if not m:
                return None
            file_id = m.group(1)

            embed_url = f"https://www.mp4upload.com/embed-{file_id}.html"
            html = self._fetch(embed_url)

            # Look for direct video URL in player source
            m = re.search(r'src:\s*["\']?(https?://[^"\']+\.mp4[^"\']*)', html)
            if m:
                return m.group(1)
        except Exception:
            pass
        return None
