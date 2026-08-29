"""Base resolver interface."""

from abc import ABC, abstractmethod
from ..config import load_config
import urllib.request
import ssl

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


class BaseResolver(ABC):
    """Base class for hoster resolvers."""

    @property
    def name(self) -> str:
        return self.__class__.__name__.replace("Resolver", "").lower()

    @abstractmethod
    def resolve(self, url: str) -> str | None:
        """Resolve a hoster URL to a direct download URL.
        
        Returns the direct download URL, or None if resolution fails.
        """
        pass

    def _fetch(self, url: str, timeout: int = 30, headers: dict | None = None) -> str:
        """Fetch a URL with the configured user agent."""
        config = load_config()
        hdrs = {"User-Agent": config.user_agent}
        if headers:
            hdrs.update(headers)
        req = urllib.request.Request(url, headers=hdrs)
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=timeout)
        return resp.read().decode("utf-8", errors="replace")

    def _fetch_json(self, url: str, timeout: int = 15, headers: dict | None = None) -> dict:
        """Fetch JSON from a URL."""
        import json
        return json.loads(self._fetch(url, timeout, headers))

    def _post(self, url: str, data: str, headers: dict | None = None, timeout: int = 15) -> dict:
        """POST data to a URL and return JSON response."""
        import json
        config = load_config()
        hdrs = {"User-Agent": config.user_agent, "Content-Type": "application/x-www-form-urlencoded"}
        if headers:
            hdrs.update(headers)
        req = urllib.request.Request(url, data=data.encode(), headers=hdrs)
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=timeout)
        return json.loads(resp.read().decode())
