#!/usr/bin/env python3
"""
WitAnime Episode Downloader v3
Downloads anime episodes from witanime.you
Phase 1: Extracts all encrypted download links
Phase 2: Downloads via mediafire (direct ZIP links, most reliable)
"""

import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.parse
import ssl
import signal

# ─── Configuration ──────────────────────────────────────────────────────────

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "anime_downloads")
DELAY = 2  # seconds between requests (be polite)

ANIME_LIST = [
    {
        "name": "Crowned in a Hundred Days",
        "short": "crowned",
        "slug": "crowned-in-a-hundred-days-bai-ri-cheng-wang",
        "episodes": range(1, 21),
    },
    {
        "name": "Tensei shitara Slime Datta Ken 4th Season",
        "short": "slime",
        "slug": "tensei-shitara-slime-datta-ken-4th-season",
        "episodes": range(10, 21),
    },
]

HOSTER_PRIORITY = ["mp4upload", "mediafire", "hexload", "gofile", "workupload", "wahmi", "streamwish", "videa", "yonaplay"]

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def log(msg):
    print(msg, flush=True)


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req, context=ssl_ctx, timeout=timeout).read().decode("utf-8", errors="replace")


def xor_decrypt(hex_str, key):
    out = ""
    for i in range(0, len(hex_str), 2):
        out += chr(int(hex_str[i : i + 2], 16) ^ ord(key[i // 2 % len(key)]))
    return out


# ─── WitAnime Link Decryption ───────────────────────────────────────────────


def extract_download_links(html):
    """Extract and decrypt all download links from a WitAnime episode page."""
    m_r = re.search(r'var _m\s*=\s*\{[^}]*"r":"([^"]+)"', html)
    b_l = re.search(r'var _b\s*=\s*\{"l":"(\d+)"\}', html)
    x_match = re.search(r"var _x\s*=\s*(\[.*?\]);", html)
    if not (m_r and b_l and x_match):
        return []

    secret = base64.b64decode(m_r.group(1)).decode()
    count = int(b_l.group(1))
    x_arr = json.loads(x_match.group(1))

    labels = re.findall(r'data-index="(\d+)".*?<span class="notice">(\w+)</span>', html, re.DOTALL)
    label_map = {int(idx): name for idx, name in labels}

    results = []
    for i in range(count):
        pi_match = re.search(r"var _p%d\s*=\s*(\[.*?\]);" % i, html)
        if not pi_match:
            continue
        chunks = json.loads(pi_match.group(1))
        seq = json.loads(xor_decrypt(x_arr[i], secret))
        decrypted = [xor_decrypt(c, secret) for c in chunks]
        arranged = [""] * len(seq)
        for j, s in enumerate(seq):
            arranged[s] = decrypted[j]
        final_url = "".join(arranged)
        hoster = label_map.get(i, "unknown")

        # Detect quality from URL
        quality = "FHD"
        url_lower = final_url.lower()
        if "+sd+" in url_lower or "-sd." in url_lower or "_sd." in url_lower:
            quality = "SD"
        elif "+hd+" in url_lower or "-hd." in url_lower or "_hd." in url_lower:
            quality = "HD"

        results.append({"index": i, "hoster": hoster, "url": final_url, "quality": quality})

    return results


def select_best_link(links):
    """Pick the best download link - prefer mediafire (direct download) for FHD."""
    if not links:
        return None

    def score(link):
        q = {"FHD": 3, "HD": 2, "SD": 1}.get(link["quality"], 0)
        h_name = link["hoster"].lower()
        # Prioritize mediafire (direct download), then hexload (API), then others
        if "mediafire" in h_name:
            h_score = 300
        elif "hexload" in h_name:
            h_score = 200
        elif "gofile" in h_name:
            h_score = 150
        elif "mp4upload" in h_name:
            h_score = 50
        else:
            h_score = 10
        return (q, h_score)

    return sorted(links, key=score, reverse=True)[0]


# ─── Hoster Resolvers ───────────────────────────────────────────────────────


def resolve_mediafire(url):
    """Extract direct download URL from mediafire page."""
    try:
        html = fetch(url)
        m = re.search(r'href="(https?://download\d+\.mediafire\.com/[^"]+)"', html)
        if m:
            return m.group(1)
    except Exception as e:
        log(f"    [WARN] Mediafire error: {e}")
    return None


def resolve_mp4upload(url):
    """Extract direct video URL from mp4upload embed page."""
    try:
        # Extract file ID from URL
        m = re.search(r'mp4upload\.com/(\w+)', url)
        if not m:
            return None
        file_id = m.group(1)

        # Fetch the embed page
        embed_url = f"https://www.mp4upload.com/embed-{file_id}.html"
        html = fetch(embed_url)

        # Look for direct video URL in the player source
        m = re.search(r'src:\s*["\x27](https?://[^"\x27]+\.mp4[^"\x27]*)', html)
        if m:
            return m.group(1)
    except Exception as e:
        log(f"    [WARN] Mp4upload resolve error: {e}")
    return None


def resolve_hexload(url):
    """Extract direct download URL from hexload using their AJAX API."""
    try:
        # Extract file ID from URL
        m = re.search(r'hexload\.com/(\w+)', url)
        if not m:
            return None
        file_id = m.group(1)

        # Call the hexload download API
        api_url = "https://hexload.com/download"
        data = f"op=download3&id={file_id}&ajax=1&method_free=1".encode()
        req = urllib.request.Request(
            api_url,
            data=data,
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=15)
        result = json.loads(resp.read().decode())

        if result.get("status") == 200 and result.get("result", {}).get("url"):
            return result["result"]["url"]
    except Exception as e:
        log(f"    [WARN] Hexload API error: {e}")
    return None


def download_wget(url, filepath, timeout=900):
    """Download using wget with generous timeout."""
    cmd = [
        "wget", "-q",
        "-O", filepath,
        "--timeout=60", "--tries=3",
        "--user-agent=" + USER_AGENT,
        "--referer=" + ("https://www.mp4upload.com/" if "mp4upload" in url else "https://witanime.you/"),
        "--content-disposition",
        url,
    ]
    try:
        result = subprocess.run(cmd, timeout=timeout, capture_output=True)
        if result.returncode == 0 and os.path.exists(filepath):
            size = os.path.getsize(filepath)
            if size > 50 * 1024:  # at least 50KB
                return True
            else:
                os.remove(filepath)
                return False
    except subprocess.TimeoutExpired:
        log(f"    [WARN] Download timed out after {timeout}s")
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        log(f"    [WARN] wget error: {e}")
    return False


def download_curl(url, filepath, timeout=900):
    """Download using curl with generous timeout."""
    referer = "https://www.mp4upload.com/" if "mp4upload" in url else "https://witanime.you/"
    cmd = [
        "curl", "-L", "-o", filepath,
        "-H", f"User-Agent: {USER_AGENT}",
        "-H", f"Referer: {referer}",
        "--connect-timeout", "30",
        "--max-time", str(timeout),
        "--silent",
        url,
    ]
    try:
        result = subprocess.run(cmd, timeout=timeout + 30, capture_output=True)
        if result.returncode == 0 and os.path.exists(filepath):
            size = os.path.getsize(filepath)
            if size > 50 * 1024:
                return True
            else:
                os.remove(filepath)
                return False
    except subprocess.TimeoutExpired:
        log(f"    [WARN] curl timed out")
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        log(f"    [WARN] curl error: {e}")
    return False


def download_file(url, filepath, timeout=900):
    """Try wget then curl."""
    if download_wget(url, filepath, timeout):
        return True
    if download_curl(url, filepath, timeout):
        return True
    return False


def get_episode_url(slug, ep_num):
    encoded = urllib.parse.quote(f"\u0627\u0644\u062d\u0644\u0642\u0629-{ep_num}")
    return f"https://witanime.you/episode/{slug}-{encoded}/"


# ─── Main ────────────────────────────────────────────────────────────────────


def process_anime(anime):
    anime_dir = os.path.join(DOWNLOAD_DIR, anime["short"])
    os.makedirs(anime_dir, exist_ok=True)
    links_file = os.path.join(anime_dir, "all_links.txt")

    log(f"\n{'#' * 60}")
    log(f"  {anime['name']}")
    log(f"{'#' * 60}")

    all_links = {}

    # ── Phase 1: Extract links ──
    log(f"\n  Phase 1: Extracting links...")
    for ep_num in anime["episodes"]:
        ep_url = get_episode_url(anime["slug"], ep_num)
        try:
            html = fetch(ep_url)
            links = extract_download_links(html)
            best = select_best_link(links)
            all_links[ep_num] = {"links": links, "best": best}

            if best:
                log(f"  EP{ep_num:02d}: [{best['quality']}] {best['hoster']} ({len(links)} total)")
            else:
                log(f"  EP{ep_num:02d}: NO LINKS")
        except Exception as e:
            log(f"  EP{ep_num:02d}: ERROR - {e}")
        time.sleep(DELAY)

    # Save all links
    with open(links_file, "w", encoding="utf-8") as f:
        f.write(f"{anime['name']} - Download Links\n{'=' * 60}\n\n")
        for ep_num in anime["episodes"]:
            info = all_links.get(ep_num, {})
            best = info.get("best")
            links = info.get("links", [])
            f.write(f"\n--- Episode {ep_num:02d} ---\n")
            if best:
                f.write(f"  >>> BEST: [{best['quality']}] {best['hoster']}: {best['url']}\n")
            for l in links:
                f.write(f"    [{l['quality']}] {l['hoster']}: {l['url']}\n")
    log(f"\n  Links saved: {links_file}")

    # ── Phase 2: Download ──
    log(f"\n  Phase 2: Downloading...")
    success = 0
    failed = 0

    for ep_num in anime["episodes"]:
        info = all_links.get(ep_num, {})
        best = info.get("best")

        filename = f"{anime['short']}_ep{ep_num:02d}.mp4"
        filepath = os.path.join(anime_dir, filename)

        # Skip if already downloaded (.mp4 or .zip)
        zip_path = os.path.join(anime_dir, f"{anime['short']}_ep{ep_num:02d}.zip")
        if (os.path.exists(filepath) and os.path.getsize(filepath) > 50 * 1024) or \
           (os.path.exists(zip_path) and os.path.getsize(zip_path) > 50 * 1024):
            target = filepath if os.path.exists(filepath) else zip_path
            log(f"  EP{ep_num:02d}: Already downloaded ({os.path.getsize(target) // (1024*1024)}MB)")
            success += 1
            continue

        if not best:
            log(f"  EP{ep_num:02d}: No links available - SKIP")
            failed += 1
            continue

        log(f"\n  EP{ep_num:02d}: [{best['quality']}] {best['hoster']}")

        downloaded = False

        # Try mediafire first (most reliable for automated download)
        mediafire_links = [l for l in info["links"] if "mediafire" in l["hoster"].lower()]
        for link in mediafire_links:
            direct_url = resolve_mediafire(link["url"])
            if direct_url:
                zip_path = os.path.join(anime_dir, f"{anime['short']}_ep{ep_num:02d}.zip")
                if download_file(direct_url, zip_path):
                    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
                    log(f"  EP{ep_num:02d}: Downloaded ({size_mb:.1f} MB)")
                    downloaded = True
                    break
            time.sleep(1)

        # Try hexload if mediafire failed (has a working API)
        if not downloaded:
            hexload_links = [l for l in info["links"] if "hexload" in l["hoster"].lower()]
            for link in hexload_links[:1]:
                direct_url = resolve_hexload(link["url"])
                if direct_url:
                    log(f"    [INFO] Got hexload direct URL")
                    if download_file(direct_url, filepath):
                        size_mb = os.path.getsize(filepath) / (1024 * 1024)
                        log(f"  EP{ep_num:02d}: Downloaded from hexload ({size_mb:.1f} MB)")
                        downloaded = True
                        break
                time.sleep(1)

        # Try mp4upload embed page (has direct video URL)
        if not downloaded:
            mp4_links = [l for l in info["links"] if "mp4upload" in l["hoster"].lower()]
            for link in mp4_links[:1]:
                direct_url = resolve_mp4upload(link["url"])
                if direct_url:
                    log(f"    [INFO] Got mp4upload direct URL")
                    if download_file(direct_url, filepath):
                        size_mb = os.path.getsize(filepath) / (1024 * 1024)
                        log(f"  EP{ep_num:02d}: Downloaded from mp4upload ({size_mb:.1f} MB)")
                        downloaded = True
                        break
                time.sleep(1)

        if downloaded:
            success += 1
        else:
            log(f"  EP{ep_num:02d}: FAILED - manual download needed (see {links_file})")
            failed += 1

    return success, failed


def main():
    log("=" * 60)
    log("  WitAnime Downloader v3")
    log("  Crowned in a Hundred Days + Slime 4th Season")
    log("  20 episodes each")
    log("=" * 60)
    log(f"  Output: {DOWNLOAD_DIR}")

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    total_s = total_f = 0
    for anime in ANIME_LIST:
        s, f = process_anime(anime)
        total_s += s
        total_f += f

    log(f"\n{'=' * 60}")
    log(f"  COMPLETE: {total_s} downloaded, {total_f} failed (out of 40)")
    log(f"  Location: {DOWNLOAD_DIR}")
    if total_f > 0:
        log(f"\n  For failed episodes, check:")
        for anime in ANIME_LIST:
            log(f"    {os.path.join(DOWNLOAD_DIR, anime['short'], 'all_links.txt')}")
    log(f"{'=' * 60}")


if __name__ == "__main__":
    main()
