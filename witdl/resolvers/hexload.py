"""Hexload resolver — uses their AJAX download API."""

import re
from .base import BaseResolver


class HexloadResolver(BaseResolver):
    """Resolves hexload URLs to direct download links via their API."""

    def resolve(self, url: str) -> str | None:
        try:
            m = re.search(r'hexload\.com/(\w+)', url)
            if not m:
                return None
            file_id = m.group(1)

            result = self._post(
                "https://hexload.com/download",
                f"op=download3&id={file_id}&ajax=1&method_free=1",
                headers={"X-Requested-With": "XMLHttpRequest"},
            )

            if result.get("status") == 200:
                return result.get("result", {}).get("url")
        except Exception:
            pass
        return None
