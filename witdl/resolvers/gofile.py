"""Gofile resolver — uses their API (requires account token)."""

import re
from .base import BaseResolver


class GofileResolver(BaseResolver):
    """Resolves gofile URLs to direct download links via their API."""

    def resolve(self, url: str) -> str | None:
        try:
            m = re.search(r"gofile\.io/d/(\w+)", url)
            if not m:
                return None
            content_id = m.group(1)

            # Get best server
            servers = self._fetch_json("https://api.gofile.io/servers")
            if servers.get("status") != "ok":
                return None
            server = servers["data"]["servers"][0]["name"]

            # Get content
            content = self._fetch_json(
                f"https://{server}.gofile.io/contents/getcontents?contentId={content_id}"
            )
            if content.get("status") != "ok":
                return None

            # Find largest video file
            contents = content["data"]["contents"]
            best_file = None
            best_size = 0
            for cid, item in contents.items():
                if item.get("mimetype", "").startswith("video/"):
                    if item.get("size", 0) > best_size:
                        best_size = item["size"]
                        best_file = item

            if best_file:
                return best_file.get("link")
        except Exception:
            pass
        return None
