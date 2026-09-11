"""WitAnime scraper — search, browse, and decrypt download links."""

import base64
import json
import re
import time
import urllib.parse
import urllib.request
import ssl
from typing import Optional

from .config import load_config
from .models import Anime, Episode, Link, Quality, SearchResult

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

BASE_URL = "https://witanime.you"


def _fetch(url: str, timeout: int = 30) -> str:
    """Fetch a URL and return the HTML content."""
    config = load_config()
    req = urllib.request.Request(url, headers={"User-Agent": config.user_agent})
    resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=timeout)
    return resp.read().decode("utf-8", errors="replace")


def _xor_decrypt(hex_str: str, key: str) -> str:
    """XOR-decrypt a hex-encoded string with the given key."""
    out = []
    for i in range(0, len(hex_str), 2):
        out.append(chr(int(hex_str[i : i + 2], 16) ^ ord(key[i // 2 % len(key)])))
    return "".join(out)


def _parse_episode_range(spec: str) -> list[int]:
    """Parse episode range like '1-5,8,10-12' into a sorted list of ints."""
    episodes = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            episodes.update(range(int(start), int(end) + 1))
        else:
            episodes.add(int(part))
    return sorted(episodes)


# ─── Search & Browse ────────────────────────────────────────────────────────


def _decode_episode_data(html: str) -> list[dict]:
    """Decode the encrypted processedEpisodeData JS variable from an anime page.
    
    WitAnime now loads episodes dynamically via JavaScript. The episode data is
    stored in a JS variable as base64.b64encode(XOR_encrypted_json) + '.' + base64.b64encode(key).
    
    Returns a list of dicts with keys: number, url, type, screenshot.
    """
    match = re.search(r"var processedEpisodeData\s*=\s*'([^']+)'", html)
    if not match:
        return []
    try:
        data = match.group(1)
        if '.' not in data:
            return []
        parts = data.split('.', 1)
        decoded_data = base64.b64decode(parts[0])
        decoded_key = base64.b64decode(parts[1])
        key_len = len(decoded_key)
        result = ""
        for i in range(len(decoded_data)):
            result += chr(decoded_data[i] ^ decoded_key[i % key_len])
        return json.loads(result)
    except Exception:
        return []


def search(query: str) -> list[SearchResult]:
    """Search WitAnime for anime matching the query.
    
    WitAnime search returns episode links, so we extract unique anime from them.
    """
    url = f"{BASE_URL}/?s={urllib.parse.quote(query)}"
    html = _fetch(url)

    # Extract unique anime slugs from episode links
    seen_slugs = set()
    results = []

    # Pattern: episode URLs contain the anime slug
    # URLs use %d8%a7 (URL-encoded Arabic) for الحلقة
    # e.g., /episode/tensei-shitara-slime-datta-ken-4th-season-%d8%a7...-20/
    ep_pattern = r'/episode/([a-z0-9-]+)-%d8%a7'
    for m in re.finditer(ep_pattern, html):
        slug = m.group(1)
        if slug not in seen_slugs:
            seen_slugs.add(slug)
            name = slug.replace("-", " ").title()
            anime_url = f"{BASE_URL}/anime/{slug}/"
            results.append(SearchResult(name=name, url=anime_url))

    # Also try direct anime links
    for m in re.finditer(r'href="(https?://witanime\.you/anime/[^"\s]+)"', html):
        anime_url = m.group(1).rstrip("/")
        slug = anime_url.split("/")[-1]
        if slug not in seen_slugs:
            seen_slugs.add(slug)
            name = slug.replace("-", " ").title()
            results.append(SearchResult(name=name, url=anime_url))

    # Fallback: extract from episode h2 titles
    if not results:
        for m in re.finditer(r'<h2><a href="[^"]+/episode/([a-z0-9-]+)-%d8%a7', html):
            slug = m.group(1)
            if slug not in seen_slugs:
                seen_slugs.add(slug)
                name = slug.replace("-", " ").title()
                results.append(SearchResult(name=name, url=f"{BASE_URL}/anime/{slug}/"))

    return results


def get_anime_info(anime_url: str) -> Optional[Anime]:
    """Get anime details and list of episode URLs from an anime page."""
    html = _fetch(anime_url)

    # Extract anime name
    name_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
    name = name_match.group(1).strip() if name_match else "Unknown"

    # Extract slug from URL
    slug = anime_url.rstrip("/").split("/")[-1]

    # Preferred: decode encrypted episode data from JS variable (has real URLs)
    episodes = []
    for ep_data in _decode_episode_data(html):
        try:
            ep_num = int(ep_data["number"])
        except (ValueError, KeyError, TypeError):
            continue
        ep_url = ep_data.get("url", "")
        if ep_url.startswith("/"):
            ep_url = BASE_URL + ep_url
        episodes.append(Episode(number=ep_num, url=ep_url))

    # Fallback: extract episode links from legacy HTML format
    if not episodes:
        ep_pattern = r'href="(https?://witanime\.you/episode/([^"]+))"'
        seen_urls = set()
        for m in re.finditer(ep_pattern, html):
            ep_url = m.group(1)
            ep_slug = m.group(2)
            if ep_url not in seen_urls:
                seen_urls.add(ep_url)
                # Extract episode number from slug
                ep_num_match = re.search(r'-(\d+)/?$', ep_slug)
                if ep_num_match:
                    ep_num = int(ep_num_match.group(1))
                    episodes.append(Episode(number=ep_num, url=ep_url))

    episodes.sort(key=lambda e: e.number)

    return Anime(
        name=name,
        slug=slug,
        url=anime_url,
        episodes=episodes,
    )


def get_episode_url(anime_slug: str, episode_num: int) -> str:
    """Construct the URL for a specific episode."""
    encoded = urllib.parse.quote(f"\u0627\u0644\u062d\u0644\u0642\u0629-{episode_num}")
    return f"{BASE_URL}/episode/{anime_slug}-{encoded}/"


# ─── Link Decryption ────────────────────────────────────────────────────────


def extract_download_links(html: str) -> list[Link]:
    """Extract and decrypt all download links from a WitAnime episode page."""
    m_r = re.search(r'var _m\s*=\s*\{[^}]*"r":"([^"]+)"', html)
    b_l = re.search(r'var _b\s*=\s*\{"l":"(\d+)"\}', html)
    x_match = re.search(r"var _x\s*=\s*(\[.*?\]);", html)
    if not (m_r and b_l and x_match):
        return []

    secret = base64.b64decode(m_r.group(1)).decode()
    count = int(b_l.group(1))
    x_arr = json.loads(x_match.group(1))

    labels = re.findall(
        r'data-index="(\d+)".*?<span class="notice">(\w+)</span>', html, re.DOTALL
    )
    label_map = {int(idx): name for idx, name in labels}

    results = []
    for i in range(count):
        pi_match = re.search(r"var _p%d\s*=\s*(\[.*?\]);" % i, html)
        if not pi_match:
            continue
        chunks = json.loads(pi_match.group(1))
        seq = json.loads(_xor_decrypt(x_arr[i], secret))
        decrypted = [_xor_decrypt(c, secret) for c in chunks]
        arranged = [""] * len(seq)
        for j, s in enumerate(seq):
            arranged[s] = decrypted[j]
        final_url = "".join(arranged)
        hoster = label_map.get(i, "unknown")

        # Detect quality from URL
        quality = Quality.FHD
        url_lower = final_url.lower()
        if "+sd+" in url_lower or "-sd." in url_lower or "_sd." in url_lower:
            quality = Quality.SD
        elif "+hd+" in url_lower or "-hd." in url_lower or "_hd." in url_lower:
            quality = Quality.HD

        results.append(Link(hoster=hoster, url=final_url, quality=quality))

    return results


def fetch_episode_links(
    anime_slug: str, episode_num: int, episode_url: str | None = None
) -> list[Link]:
    """Fetch and decrypt download links for a specific episode.

    Uses the real episode URL when known (movies/specials don't follow the
    numeric episode URL pattern); otherwise constructs one from the slug.
    """
    ep_url = episode_url or get_episode_url(anime_slug, episode_num)
    html = _fetch(ep_url)
    return extract_download_links(html)


def fetch_all_episodes(anime: Anime) -> Anime:
    """Fetch download links for all episodes of an anime. Modifies in place."""
    config = load_config()
    for ep in anime.episodes:
        try:
            ep.links = fetch_episode_links(anime.slug, ep.number, ep.url or None)
        except Exception as e:
            print(f"  [WARN] EP{ep.number:02d}: {e}")
        time.sleep(config.delay_between_episodes)
    return anime


# ─── Search + Auto-detect ───────────────────────────────────────────────────


def search_and_detect(url_or_query: str) -> Optional[Anime]:
    """Given a URL or search query, return an Anime with episode info.
    
    Supports:
    - Direct anime URLs
    - Direct episode URLs (auto-detects parent anime)
    - Search result URLs (e.g. ?search_param=animes&s=QUERY)
    - Search queries (picks first result)
    """
    # Normalize scheme-less URLs, e.g. "witanime.you/anime/foo/"
    if not url_or_query.startswith(("http://", "https://")) and "witanime.you" in url_or_query:
        url_or_query = "https://" + url_or_query.lstrip("/")

    # Direct episode URL (episodes, movies, specials, ...)
    if "/episode/" in url_or_query:
        # Best effort: fetch the episode page and follow its anime link
        anime = _detect_anime_from_episode_url(url_or_query)
        if anime:
            return anime
        # Fallback: guess the anime from the slug pattern
        m = re.search(r'/episode/([^/]+?)-(?:%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9|الحلقة)-(\d+)', url_or_query)
        if m:
            return _detect_anime_from_episode_slug(m.group(1))
        return None

    # Direct anime URL
    if "/anime/" in url_or_query:
        return get_anime_info(url_or_query)

    # Search URL with query parameter (e.g. ?search_param=animes&s=QUERY)
    search_match = re.search(r'[?&]s=([^&]+)', url_or_query)
    if search_match:
        query = urllib.parse.unquote(search_match.group(1))
        results = search(query)
        if results:
            return get_anime_info(results[0].url)
        return None

    # Search query
    results = search(url_or_query)
    if results:
        return get_anime_info(results[0].url)

    return None


def _detect_anime_from_episode_url(episode_url: str) -> Optional[Anime]:
    """Detect the parent anime by reading the anime link off an episode page.

    More reliable than parsing the slug, since movies/specials use different
    URL shapes (e.g. /episode/فيلم-the-ribbon-hero/).
    """
    try:
        html = _fetch(episode_url)
    except Exception:
        return None
    m = re.search(r'href="(https?://witanime\.you/anime/[^"]+)"', html)
    if not m:
        return None
    return get_anime_info(m.group(1))


def _detect_anime_from_episode_slug(ep_slug: str) -> Optional[Anime]:
    """Detect the anime from an episode slug by trying common patterns."""
    # Try searching for the anime name extracted from the episode slug
    # e.g., "crowned-in-a-hundred-days-bai-ri-cheng-wang" -> search for "crowned in a hundred days"
    clean = re.sub(r'-bai-ri-cheng-wang$', '', ep_slug)
    clean = re.sub(r'-\d+$', '', clean)
    query = clean.replace("-", " ")

    results = search(query)
    if results:
        return get_anime_info(results[0].url)
    return None
