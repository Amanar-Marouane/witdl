# 🎬 WitDL — Advanced WitAnime Downloader

> **Version: 0.1.0**

Download anime from [WitAnime](https://witanime.you) with search, multi-hoster support, concurrent downloads, auto-watch, and library management.

## Features

| Feature | Description |
|---------|-------------|
| 🔍 **Search** | Find anime by name directly from the terminal |
| ℹ️ **Info** | View anime details (episodes, URL, slug) |
| 📥 **Download** | Download episodes with multi-hoster fallback |
| ⚡ **Concurrent** | Download multiple episodes simultaneously |
| ⏯️ **Resume** | Interrupted downloads resume automatically |
| 🔄 **Retry** | Failed downloads retry with exponential backoff |
| 👁️ **Watch** | Auto-download new episodes as they release |
| 📚 **Library** | Track what's downloaded, find missing episodes |
| ⚙️ **Config** | Customize quality, hosters, concurrency, paths |

## Install

```bash
cd witdl
chmod +x witdl.sh
./witdl.sh --version  # Should print "WitDL 0.1.0"
```

Or make it globally available:

```bash
ln -sf $(pwd)/witdl.sh ~/.local/bin/witdl
# Open a new terminal, then just type:
witdl --version
```

## Quick Start

```bash
# Search for anime
witdl search "slime datta ken"

# See details
witdl info "slime datta ken 4th"

# Download episodes 10-20
witdl download "slime datta ken 4th" --episodes 10-20

# Download from URL
witdl download https://witanime.you/anime/tensei-shitara-slime-datta-ken-4th-season/ --episodes 1-20

# Watch for new episodes
witdl watch "slime datta ken 4th" --interval 30

# Check library
witdl list
witdl missing "slime datta ken 4th"
```

## Commands Reference

### `witdl search <query>`

Search WitAnime for anime matching the query.

```bash
witdl search "slime"
witdl search "crowned in a hundred days"
witdl search "one piece"
```

Output:
```
🔍 Searching for: slime

  1. Tensei Shitara Slime Datta Ken 4Th Season
     https://witanime.you/anime/tensei-shitara-slime-datta-ken-4th-season/

  Found 1 result(s).
```

---

### `witdl info <url_or_query>`

Show anime details.

```bash
witdl info "slime datta ken 4th"
witdl info https://witanime.you/anime/tensei-shitara-slime-datta-ken-4th-season/
```

Output:
```
📺 Fetching info: slime datta ken 4th

  Name:     Tensei shitara Slime Datta Ken 4th Season
  Slug:     tensei-shitara-slime-datta-ken-4th-season
  Episodes: 50
  URL:      https://witanime.you/anime/tensei-shitara-slime-datta-ken-4th-season/
```

---

### `witdl download <url_or_query> [options]`

Download anime episodes.

```bash
# Download specific episodes
witdl download "slime" --episodes 1-20
witdl download "crowned" --episodes 1,3,5,7-12

# Download from URL
witdl download https://witanime.you/anime/slime-... --episodes 10-20

# Specify quality
witdl download "slime" --episodes 1-5 --quality fhd
```

**Episode range syntax:**
- `1-20` → episodes 1 through 20
- `1,3,5` → episodes 1, 3, and 5
- `1-5,10,15-20` → mixed ranges

**Quality options:** `fhd` (default), `hd`, `sd`

---

### `witdl watch <anime...> [options]`

Auto-download new episodes as they release. Runs continuously until Ctrl+C.

```bash
# Watch one anime
witdl watch "slime datta ken 4th"

# Watch multiple anime
witdl watch "crowned in a hundred days" "slime datta ken 4th"

# Custom check interval (minutes)
witdl watch "slime" -i 15

# Notify only (don't auto-download)
witdl watch "slime" -n
```

**Options:**
| Flag | Description |
|------|-------------|
| `--interval`, `-i` | Check interval in minutes (default: 30) |
| `--no-download`, `-n` | Only notify about new episodes, don't download |

---

### `witdl list`

Show all downloaded anime in your library.

```bash
witdl list
```

Output:
```
📚 Your Library (2 anime)

  ✅ Crowned in a Hundred Days
     20/20 episodes (0 failed)
  🔄 Tensei shitara Slime Datta Ken 4th Season
     5/20 episodes (0 failed)
```

---

### `witdl missing <url_or_query>`

Show which episodes haven't been downloaded yet.

```bash
witdl missing "slime datta ken 4th"
```

---

### `witdl queue`

Show pending downloads (incomplete anime).

```bash
witdl queue
```

---

### `witdl retry`

Retry all previously failed downloads.

```bash
witdl retry
```

---

### `witdl clean`

Remove failed download records from state.

```bash
witdl clean
```

---

### `witdl config <action>`

Manage configuration.

```bash
# Show current config
witdl config show

# Set a value
witdl config set download_dir /mnt/hdd/anime
witdl config set quality fhd
witdl config set max_concurrent_downloads 3
witdl config set delay_between_episodes 1
witdl config set hoster_priority mediafire,hexload,mp4upload

# Interactive setup
witdl config init
```

**Config keys:**

| Key | Default | Description |
|-----|---------|-------------|
| `download_dir` | `~/anime` | Where to save downloaded episodes |
| `quality` | `fhd` | Preferred quality: `fhd`, `hd`, `sd` |
| `hoster_priority` | `mediafire,hexload,...` | Comma-separated hoster order |
| `max_concurrent_downloads` | `2` | How many episodes to download at once |
| `delay_between_episodes` | `2.0` | Seconds between episode requests |
| `timeout_per_download` | `900` | Max seconds per download (15 min) |
| `auto_retry` | `true` | Automatically retry failed downloads |
| `max_retries` | `3` | Number of retry attempts |

Config is saved at `~/.witdl/config.json`.

---

### `witdl --version`

Print the current version.

```bash
witdl --version
# WitDL 0.1.0
```

## How It Works

### Download Pipeline

1. **Search/Detect** — Find anime by name, URL, or episode link
2. **Fetch Links** — Scrape episode pages, decrypt obfuscated download URLs
3. **Resolve Hoster** — Convert hoster page URLs to direct download links
4. **Download** — Use wget/curl with resume, retry, and concurrent support
5. **Track** — Save download state to resume later

### Supported Hosters

| Hoster | Method | Reliability |
|--------|--------|-------------|
| Mediafire | Direct download URL extraction | ⭐⭐⭐ Best |
| Hexload | AJAX API (`op=download3`) | ⭐⭐⭐ Great |
| Mp4upload | Embed page video URL extraction | ⭐⭐ Good |
| Gofile | API (requires account token) | ⭐ Works |
| Workupload | Page scraping | ⭐ Works |
| Wahmi | Page scraping | ⭐ Works |

The script tries hosters in priority order. If one fails, it automatically falls back to the next.

### Link Decryption

WitAnime obfuscates download links using XOR encryption with base64-encoded keys. WitDL:
1. Extracts `_m.r` (XOR key), `_p0`–`_p3` (encrypted chunks), `_x` (reorder sequence)
2. XOR-decrypts each chunk with the key
3. Reorders chunks according to the sequence
4. Produces the final download URL

## File Structure

```
witdl/
├── witdl/                    # Main package
│   ├── __init__.py          # Version info
│   ├── __main__.py          # python3 -m witdl entry
│   ├── cli.py               # CLI with all subcommands
│   ├── config.py            # Config management
│   ├── downloader.py        # Download engine (concurrent, retry)
│   ├── library.py           # Library & state tracking
│   ├── models.py            # Data classes
│   ├── scraper.py           # WitAnime scraping & decryption
│   └── resolvers/           # Hoster resolvers
│       ├── __init__.py      # Resolver registry
│       ├── base.py          # Base resolver class
│       ├── mediafire.py     # Mediafire resolver
│       ├── hexload.py       # Hexload API resolver
│       ├── mp4upload.py     # Mp4upload embed resolver
│       └── gofile.py        # Gofile API resolver
├── witdl.sh                  # Shell wrapper
├── pyproject.toml           # Package config
├── README.md                # This file
└── .gitignore
```

## State Files

| File | Location | Purpose |
|------|----------|---------|
| Config | `~/.witdl/config.json` | User preferences |
| State | `~/.witdl/state.json` | Download history & tracking |

## Examples

```bash
# Full workflow: search → download → manage
witdl search "one piece"
witdl info "one piece"
witdl download "one piece" --episodes 1100-1120
witdl list
witdl missing "one piece"
witdl retry

# Auto-download new episodes every hour
witdl watch "one piece" -i 60

# Download 3 episodes at once
witdl config set max_concurrent_downloads 3
witdl download "slime" --episodes 1-3

 # Notify only (no download)
witdl watch "slime" -n

# Switch to external HDD
witdl config set download_dir /mnt/hdd/anime
```

## Requirements

- Python 3.10+
- `wget` and/or `curl` (for downloads)
- No external Python packages (stdlib only)

## License

MIT
