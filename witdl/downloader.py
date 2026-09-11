"""Download engine with progress, retry, resume, and hoster fallback."""

import os
import subprocess
import sys
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Optional

from .config import load_config
from .models import Episode, DownloadResult, DownloadStatus
from .resolvers import get_resolver

# Thread-safe print lock
_print_lock = threading.Lock()


@dataclass
class DownloadProgress:
    """Progress info for a single download."""
    episode: int
    filename: str
    bytes_downloaded: int = 0
    total_bytes: int = 0
    speed: float = 0.0  # bytes/sec
    eta: int = 0  # seconds remaining


def _format_size(size_bytes: int) -> str:
    """Format bytes into human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f}GB"


def _format_time(seconds: int) -> str:
    """Format seconds into human-readable time."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    else:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m}m"


class Downloader:
    """Download engine with retry, resume, and hoster fallback."""

    def __init__(self, on_progress: Optional[Callable] = None):
        self.config = load_config()
        self.on_progress = on_progress

    def download_episode(
        self,
        episode: Episode,
        output_dir: str,
        anime_short: str,
        preferred_quality: str | None = None,
    ) -> DownloadResult:
        """Download a single episode, trying multiple hosters."""
        os.makedirs(output_dir, exist_ok=True)

        # Prefer links matching the requested quality, but fall back to any
        # quality when none match so a download is still possible.
        links = list(episode.links)
        if preferred_quality:
            requested = preferred_quality.value if hasattr(preferred_quality, "value") else str(preferred_quality)
            matching = [l for l in links if l.quality.value == requested.lower()]
            if matching:
                links = matching

        for attempt in range(self.config.max_retries + 1):
            if attempt > 0:
                wait = min(2 ** attempt, 30)
                print(f"    Retry {attempt}/{self.config.max_retries} (waiting {wait}s...)")
                time.sleep(wait)

            # Try each link in priority order
            for link in links:
                result = self._try_download(link, episode.number, output_dir, anime_short)
                if result.status == DownloadStatus.COMPLETED:
                    return result

            # If all hosters failed, try resolving with different hosters
            if attempt == 0:
                # On first failure, try alternative hosters
                for link in links:
                    resolver = get_resolver(link.hoster)
                    if resolver:
                        direct_url = resolver.resolve(link.url)
                        if direct_url:
                            result = self._download_file(
                                direct_url, episode.number, output_dir, anime_short,
                                link.hoster
                            )
                            if result.status == DownloadStatus.COMPLETED:
                                return result

        return DownloadResult(
            episode_number=episode.number,
            status=DownloadStatus.FAILED,
            error="All hosters and retries exhausted",
        )

    def _try_download(
        self, link, episode_num: int, output_dir: str, anime_short: str
    ) -> DownloadResult:
        """Try to download from a specific link."""
        # Resolve to direct URL
        resolver = get_resolver(link.hoster)
        if resolver:
            direct_url = resolver.resolve(link.url)
            if direct_url:
                return self._download_file(
                    direct_url, episode_num, output_dir, anime_short, link.hoster
                )

        return DownloadResult(
            episode_number=episode_num,
            status=DownloadStatus.FAILED,
            hoster_used=link.hoster,
            error="Could not resolve direct URL",
        )

    def _download_file(
        self,
        url: str,
        episode_num: int,
        output_dir: str,
        anime_short: str,
        hoster: str,
    ) -> DownloadResult:
        """Download a file using wget/curl with resume support."""
        filename = f"{anime_short}_EP{episode_num:02d}.mp4"
        filepath = os.path.join(output_dir, filename)

        # Check if already downloaded
        if os.path.exists(filepath) and os.path.getsize(filepath) > 50 * 1024:
            return DownloadResult(
                episode_number=episode_num,
                status=DownloadStatus.COMPLETED,
                filepath=filepath,
                size_bytes=os.path.getsize(filepath),
                hoster_used=hoster,
            )

        # Try wget with resume
        if self._wget_download(url, filepath):
            return DownloadResult(
                episode_number=episode_num,
                status=DownloadStatus.COMPLETED,
                filepath=filepath,
                size_bytes=os.path.getsize(filepath),
                hoster_used=hoster,
            )

        # Try curl with resume
        if self._curl_download(url, filepath):
            # Extract video from ZIP if the hoster wrapped it
            extracted = self._extract_zip_if_needed(filepath)
            return DownloadResult(
                episode_number=episode_num,
                status=DownloadStatus.COMPLETED,
                filepath=extracted or filepath,
                size_bytes=os.path.getsize(extracted or filepath),
                hoster_used=hoster,
            )

        # Cleanup failed download
        for ext in ["", ".part", ".tmp"]:
            p = filepath + ext
            if os.path.exists(p):
                os.remove(p)

        return DownloadResult(
            episode_number=episode_num,
            status=DownloadStatus.FAILED,
            hoster_used=hoster,
            error="Download failed",
        )

    def _extract_zip_if_needed(self, filepath: str) -> str | None:
        """If the downloaded file is a ZIP archive containing a video, extract it.
        
        Some hosters (e.g. mp4upload) wrap the video in a ZIP file.
        Returns the path to the extracted video file, or None if not a ZIP.
        """
        try:
            # Check ZIP magic bytes
            with open(filepath, 'rb') as f:
                magic = f.read(4)
            if magic != b'PK\x03\x04':
                return None

            with zipfile.ZipFile(filepath, 'r') as zf:
                # Find the first video file in the archive
                video_exts = ('.mp4', '.mkv', '.avi', '.webm', '.mov')
                video_name = None
                for name in zf.namelist():
                    if name.lower().endswith(video_exts):
                        video_name = name
                        break

                if not video_name:
                    return None

                print(f"    📦 Extracting {os.path.basename(video_name)} from ZIP...")

                # Extract the video to the same directory as the original file
                output_dir = os.path.dirname(filepath)
                extracted_path = os.path.join(output_dir, video_name)
                with zf.open(video_name) as src, open(extracted_path, 'wb') as dst:
                    while True:
                        chunk = src.read(1024 * 1024)
                        if not chunk:
                            break
                        dst.write(chunk)

                # Rename to match the original expected filename if different
                if extracted_path != filepath:
                    final_path = filepath
                    # Remove ZIP file first
                    os.remove(filepath)
                    # Rename extracted file to expected name
                    os.rename(extracted_path, final_path)
                    return final_path

                return extracted_path

        except (zipfile.BadZipFile, Exception):
            return None

    def _wget_download(self, url: str, filepath: str) -> bool:
        """Download using wget with resume support."""
        referer = "https://www.mp4upload.com/" if "mp4upload" in url else "https://witanime.you/"
        cmd = [
            "wget", "-q", "-c",
            "-O", filepath,
            "--timeout=60", "--tries=3",
            f"--user-agent={self.config.user_agent}",
            f"--referer={referer}",
            url,
        ]
        try:
            result = subprocess.run(
                cmd, timeout=self.config.timeout_per_download, capture_output=True
            )
            return result.returncode == 0 and os.path.exists(filepath) and os.path.getsize(filepath) > 50 * 1024
        except (subprocess.TimeoutExpired, Exception):
            return False

    def _curl_download(self, url: str, filepath: str) -> bool:
        """Download using curl with resume support."""
        referer = "https://www.mp4upload.com/" if "mp4upload" in url else "https://witanime.you/"
        cmd = [
            "curl", "-L", "-C", "-",
            "-o", filepath,
            "-H", f"User-Agent: {self.config.user_agent}",
            "-H", f"Referer: {referer}",
            "--connect-timeout", "30",
            "--max-time", str(self.config.timeout_per_download),
            "--silent",
            url,
        ]
        try:
            result = subprocess.run(
                cmd, timeout=self.config.timeout_per_download + 30, capture_output=True
            )
            return result.returncode == 0 and os.path.exists(filepath) and os.path.getsize(filepath) > 50 * 1024
        except (subprocess.TimeoutExpired, Exception):
            return False

    def _download_one(
        self,
        ep: Episode,
        output_dir: str,
        anime_short: str,
        on_done: Optional[Callable],
        quality: str | None = None,
    ) -> DownloadResult:
        """Download a single episode (thread-safe)."""
        with _print_lock:
            print(f"\n  EP{ep.number:02d}: [{ep.best_link.quality.display if ep.best_link else '?'}] "
                  f"{ep.best_link.hoster if ep.best_link else 'no links'}")

        result = self.download_episode(ep, output_dir, anime_short, preferred_quality=quality)

        with _print_lock:
            if result.status == DownloadStatus.COMPLETED:
                print(f"  EP{ep.number:02d}: ✅ Done ({_format_size(result.size_bytes)})")
            else:
                print(f"  EP{ep.number:02d}: ❌ Failed — {result.error}")
            sys.stdout.flush()

        if on_done:
            on_done(result)

        return result

    def download_anime(
        self,
        anime_name: str,
        anime_short: str,
        episodes: list[Episode],
        on_episode_done: Optional[Callable] = None,
        quality: str | None = None,
    ) -> tuple[int, int]:
        """Download all episodes concurrently. Returns (success_count, fail_count)."""
        output_dir = os.path.join(self.config.download_dir, anime_name)
        os.makedirs(output_dir, exist_ok=True)

        max_workers = self.config.max_concurrent_downloads
        success = 0
        failed = 0

        if max_workers <= 1 or len(episodes) <= 1:
            # Sequential mode
            for ep in episodes:
                result = self._download_one(
                    ep, output_dir, anime_short, on_episode_done, quality
                )
                if result.status == DownloadStatus.COMPLETED:
                    success += 1
                else:
                    failed += 1
                time.sleep(self.config.delay_between_episodes)
        else:
            # Concurrent mode
            with _print_lock:
                print(f"  ⚡ Downloading with {max_workers} concurrent connections\n")

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for ep in episodes:
                    future = executor.submit(
                        self._download_one,
                        ep, output_dir, anime_short, on_episode_done, quality,
                    )
                    futures[future] = ep.number
                    # Small stagger to avoid hammering the server
                    time.sleep(0.5)

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result.status == DownloadStatus.COMPLETED:
                            success += 1
                        else:
                            failed += 1
                    except Exception as e:
                        ep_num = futures[future]
                        with _print_lock:
                            print(f"  EP{ep_num:02d}: ❌ Exception — {e}")
                        failed += 1

        return success, failed
