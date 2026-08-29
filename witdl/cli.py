"""WitDL CLI — command-line interface for the WitAnime downloader."""

import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .config import Config, load_config
from .library import Library
from .models import Episode, DownloadStatus, Quality
from .downloader import Downloader, _format_size
from .scraper import (
    search, get_anime_info, fetch_all_episodes, fetch_episode_links,
    _parse_episode_range, search_and_detect
)


def cmd_search(args):
    """Search for anime on WitAnime."""
    print(f"\n🔍 Searching for: {args.query}\n")
    results = search(args.query)
    if not results:
        print("  No results found.")
        return
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r.name}")
        print(f"     {r.url}")
    print(f"\n  Found {len(results)} result(s).")
    print(f"  Use 'witdl info <url>' to see details, or 'witdl download <url>' to download.")


def cmd_info(args):
    """Show anime details."""
    print(f"\n📺 Fetching info: {args.url_or_query}\n")
    anime = search_and_detect(args.url_or_query)
    if not anime:
        print("  Could not find anime.")
        return

    print(f"  Name:     {anime.name}")
    print(f"  Slug:     {anime.slug}")
    print(f"  Episodes: {anime.episode_count}")
    print(f"  URL:      {anime.url}")
    if anime.episodes:
        nums = [str(e.number) for e in anime.episodes]
        print(f"  Available: {', '.join(nums)}")


def cmd_download(args):
    """Download anime episodes."""
    config = load_config()
    library = Library()

    # Parse episode range
    episodes_to_download = None
    if args.episodes:
        episodes_to_download = _parse_episode_range(args.episodes)

    # Resolve the anime
    print(f"\n🔎 Resolving: {args.url_or_query}\n")
    anime = search_and_detect(args.url_or_query)
    if not anime:
        print("  ❌ Could not find anime.")
        return

    print(f"  📺 {anime.name}")
    print(f"  📁 {anime.episode_count} episodes available\n")

    # Filter episodes if specified
    if episodes_to_download:
        anime.episodes = [e for e in anime.episodes if e.number in episodes_to_download]
        print(f"  📋 Selected episodes: {args.episodes}")
        print(f"     ({len(anime.episodes)} episodes to process)\n")

    # Fetch download links
    print("  Phase 1: Fetching download links...")
    anime = fetch_all_episodes(anime)

    # Check library for already downloaded
    lib_anime = library.get_or_create_anime(anime.name, anime.slug)
    skipped = 0
    to_download = []
    for ep in anime.episodes:
        if library.is_downloaded(anime.slug, ep.number):
            print(f"  EP{ep.number:02d}: ⏭️  Already downloaded")
            skipped += 1
            continue
        if not ep.links:
            print(f"  EP{ep.number:02d}: ⚠️  No download links found")
            continue
        to_download.append(ep)

    print(f"\n  📥 {len(to_download)} to download, {skipped} skipped\n")

    if not to_download:
        print("  Nothing to download!")
        return

    # Create short name for files
    anime_short = anime.slug.split("-")[0][:20]

    # Download
    print("  Phase 2: Downloading...\n")
    downloader = Downloader()

    def on_done(result):
        library.update_episode(anime.slug, result)

    success, failed = downloader.download_anime(
        anime_name=anime.name,
        anime_short=anime_short,
        episodes=to_download,
        on_episode_done=on_done,
    )

    # Summary
    print(f"\n{'='*60}")
    print(f"  ✅ {success} downloaded, ❌ {failed} failed, ⏭️  {skipped} skipped")
    print(f"  📁 {os.path.join(config.download_dir, anime.name)}")
    if failed > 0:
        print(f"  💡 Run 'witdl retry' to retry failed downloads")
    print(f"{'='*60}\n")


def cmd_list(args):
    """List downloaded anime."""
    library = Library()
    items = library.list_all()

    if not items:
        print("\n  📭 Library is empty. Use 'witdl download <url>' to get started.\n")
        return

    print(f"\n📚 Your Library ({len(items)} anime)\n")
    for slug, info in items.items():
        status = "✅" if info["downloaded"] == info["total"] else "🔄"
        print(f"  {status} {info['name']}")
        print(f"     {info['downloaded']}/{info['total']} episodes "
              f"({info['failed']} failed)")
    print()


def cmd_missing(args):
    """Show missing episodes for an anime."""
    print(f"\n🔎 Checking: {args.url_or_query}\n")
    anime = search_and_detect(args.url_or_query)
    if not anime:
        print("  Could not find anime.")
        return

    library = Library()
    downloaded = library.get_downloaded_episodes(anime.slug)
    total = anime.episode_count or 20  # fallback
    missing = library.get_missing_episodes(anime.slug, total)

    print(f"  📺 {anime.name}")
    print(f"  ✅ Downloaded: {len(downloaded)}")
    print(f"  ❌ Missing:    {len(missing)}")
    if missing:
        print(f"  Episodes: {', '.join(str(n) for n in missing)}")
    print()


def cmd_retry(args):
    """Retry failed downloads."""
    library = Library()
    items = library.list_all()

    failed_anime = []
    for slug, info in items.items():
        if info["failed"] > 0:
            failed_anime.append((slug, info))

    if not failed_anime:
        print("\n  ✅ No failed downloads to retry.\n")
        return

    for slug, info in failed_anime:
        print(f"\n  🔄 Retrying: {info['name']} ({info['failed']} failed)")
        anime_info = get_anime_info(f"https://witanime.you/anime/{slug}/")
        if not anime_info:
            continue

        # Get failed episode numbers
        lib_anime = library.get_anime(slug)
        if not lib_anime:
            continue
        failed_eps = [num for num, ep in lib_anime.episodes.items() if ep.status == "failed"]

        # Fetch links and retry
        for ep_num in failed_eps:
            try:
                links = fetch_episode_links(slug, ep_num)
                if links:
                    ep = Episode(number=ep_num, links=links)
                    downloader = Downloader()
                    anime_short = slug.split("-")[0][:20]
                    result = downloader.download_episode(
                        ep,
                        os.path.join(load_config().download_dir, info["name"]),
                        anime_short,
                    )
                    library.update_episode(slug, result)
            except Exception as e:
                print(f"    EP{ep_num:02d}: Error — {e}")


def cmd_clean(args):
    """Clean failed downloads."""
    library = Library()
    library.clean_failed()
    print("\n  🧹 Cleaned failed download records.\n")


def cmd_config(args):
    """Manage configuration."""
    config = load_config()

    if args.action == "show":
        print(f"\n⚙️  Current Configuration\n")
        print(f"  download_dir:        {config.download_dir}")
        print(f"  quality:             {config.quality}")
        print(f"  hoster_priority:     {', '.join(config.hoster_priority)}")
        print(f"  max_concurrent:      {config.max_concurrent_downloads}")
        print(f"  delay_between_eps:   {config.delay_between_episodes}s")
        print(f"  timeout:             {config.timeout_per_download}s")
        print(f"  auto_retry:          {config.auto_retry}")
        print(f"  max_retries:         {config.max_retries}")
        print()

    elif args.action == "set":
        if not args.key or not args.value:
            print("  Usage: witdl config set <key> <value>")
            return
        key = args.key
        value = args.value
        if hasattr(config, key):
            old = getattr(config, key)
            # Type coercion
            if isinstance(old, int):
                value = int(value)
            elif isinstance(old, float):
                value = float(value)
            elif isinstance(old, bool):
                value = value.lower() in ("true", "1", "yes")
            elif isinstance(old, list):
                value = [v.strip() for v in value.split(",")]
            setattr(config, key, value)
            config.save()
            print(f"\n  ✅ Set {key} = {value}\n")
        else:
            print(f"\n  ❌ Unknown config key: {key}")
            print(f"  Valid keys: download_dir, quality, hoster_priority, "
                  f"max_concurrent_downloads, delay_between_episodes, "
                  f"timeout_per_download, auto_retry, max_retries\n")

    elif args.action == "init":
        print("\n⚙️  WitDL Configuration Setup\n")
        config.download_dir = input(f"  Download directory [{config.download_dir}]: ").strip() or config.download_dir
        config.quality = input(f"  Quality (fhd/hd/sd) [{config.quality}]: ").strip() or config.quality
        config.max_concurrent_downloads = int(
            input(f"  Max concurrent downloads [{config.max_concurrent_downloads}]: ").strip()
            or config.max_concurrent_downloads
        )
        config.delay_between_episodes = float(
            input(f"  Delay between episodes in seconds [{config.delay_between_episodes}]: ").strip()
            or config.delay_between_episodes
        )
        config.save()
        print(f"\n  ✅ Configuration saved to ~/.witdl/config.json\n")


def cmd_queue(args):
    """Show download queue / pending items."""
    library = Library()
    items = library.list_all()

    pending = []
    for slug, info in items.items():
        if info["downloaded"] < info["total"] or info["failed"] > 0:
            pending.append((slug, info))

    if not pending:
        print("\n  ✅ No pending downloads.\n")
        return

    print(f"\n📥 Download Queue ({len(pending)} anime)\n")
    for slug, info in pending:
        remaining = info["total"] - info["downloaded"]
        print(f"  🔄 {info['name']}")
        print(f"     {info['downloaded']}/{info['total']} done, "
              f"{remaining} remaining, {info['failed']} failed")
    print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="witdl",
        description="🎬 WitDL — Advanced WitAnime Downloader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  witdl search "slime datta ken"
  witdl download "slime datta ken 4th" --episodes 10-20
  witdl download https://witanime.you/anime/slime-... --episodes 1-20
  witdl list
  witdl missing "crowned in a hundred days"
  witdl config set quality fhd
  witdl config set download_dir /mnt/hdd/anime
  witdl retry
        """
    )
    parser.add_argument("--version", action="version", version=f"WitDL {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # search
    p_search = subparsers.add_parser("search", help="Search for anime")
    p_search.add_argument("query", help="Search query")
    p_search.set_defaults(func=cmd_search)

    # info
    p_info = subparsers.add_parser("info", help="Show anime details")
    p_info.add_argument("url_or_query", help="URL or search query")
    p_info.set_defaults(func=cmd_info)

    # download
    p_dl = subparsers.add_parser("download", help="Download anime episodes")
    p_dl.add_argument("url_or_query", help="URL or search query")
    p_dl.add_argument("--episodes", "-e", help="Episode range (e.g., 1-20, 1,3,5)")
    p_dl.add_argument("--quality", "-q", choices=["fhd", "hd", "sd"], help="Quality preference")
    p_dl.set_defaults(func=cmd_download)

    # list
    p_list = subparsers.add_parser("list", help="List downloaded anime")
    p_list.set_defaults(func=cmd_list)

    # missing
    p_miss = subparsers.add_parser("missing", help="Show missing episodes")
    p_miss.add_argument("url_or_query", help="URL or search query")
    p_miss.set_defaults(func=cmd_missing)

    # retry
    p_retry = subparsers.add_parser("retry", help="Retry failed downloads")
    p_retry.set_defaults(func=cmd_retry)

    # clean
    p_clean = subparsers.add_parser("clean", help="Clean failed download records")
    p_clean.set_defaults(func=cmd_clean)

    # queue
    p_queue = subparsers.add_parser("queue", help="Show download queue")
    p_queue.set_defaults(func=cmd_queue)

    # config
    p_config = subparsers.add_parser("config", help="Manage configuration")
    config_sub = p_config.add_subparsers(dest="action")
    config_sub.add_parser("show", help="Show current config")
    config_sub.add_parser("init", help="Interactive setup")
    p_set = config_sub.add_parser("set", help="Set a config value")
    p_set.add_argument("key", help="Config key")
    p_set.add_argument("value", help="Config value")
    p_config.set_defaults(func=cmd_config)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
