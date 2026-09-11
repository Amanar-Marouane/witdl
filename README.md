# 🎬 WitDL — Advanced WitAnime Downloader

[![CI](https://github.com/OWNER/witdl/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/witdl/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

> **Version: 0.1.0** · Pre-1.0 software — interfaces may change.

Download anime from [WitAnime](https://witanime.you) with search, multi-hoster
support, concurrent downloads, auto-watch, and library management.

> ⚠️ **Legal notice:** WitDL is a tool that does not host or distribute any
> content. You are responsible for complying with copyright law and the terms of
> service of the sites you access. See [Legal and ethical use](docs/GUIDE.md#legal-and-ethical-use).

## Features

| Feature | Description |
|---------|-------------|
| 🔍 **Search** | Find anime by name directly from the terminal |
| 🔗 **URL aware** | Accepts anime, episode, movie, and search-result URLs |
| ℹ️ **Info** | View anime details (episodes, URL, slug) |
| 📥 **Download** | Download episodes with multi-hoster fallback |
| 🎞️ **Movies & specials** | Resolves non-numeric episode URLs correctly |
| ⚡ **Concurrent** | Download multiple episodes simultaneously |
| ⏯️ **Resume** | Interrupted downloads resume automatically |
| 🔄 **Retry** | Failed downloads retry with exponential backoff |
| 📦 **ZIP unwrap** | Extracts videos that hosters deliver inside ZIP archives |
| 🎚️ **Quality** | Prefer FHD/HD/SD when multiple links exist |
| 👁️ **Watch** | Auto-download new episodes as they release |
| 📚 **Library** | Track what's downloaded, find missing episodes |
| ⚙️ **Config** | Customize quality, hosters, concurrency, paths |

## Install

WitDL is a pure-Python package with **no runtime dependencies**.

```bash
git clone https://github.com/OWNER/witdl.git
cd witdl
pip install -e .
witdl --version   # WitDL 0.1.0
```

Prefer not to install? Run it from the checkout:

```bash
python -m witdl --help
# or
./witdl.sh --help
```

## Quick Start

```bash
# Search for anime
witdl search "slime datta ken"

# See details
witdl info "slime datta ken 4th"

# Download episodes 10-20
witdl download "slime datta ken 4th" --episodes 10-20

# Download from a URL (anime, episode, movie, or search-results URL)
witdl download "https://witanime.you/anime/tensei-shitara-slime-datta-ken-4th-season/" --episodes 1-20

# Recognize a URL in `search` and download it right away
witdl search --download "https://witanime.you/episode/film-the-ribbon-hero/"

# Watch for new episodes
witdl watch "slime datta ken 4th" --interval 30

# Check your library
witdl list
witdl missing "slime datta ken 4th"
```

## Commands Reference

### `witdl search <query|url>`

Search WitAnime for anime matching the query. If you pass a URL instead, WitDL
detects it and shows the anime's info (or downloads it with `--download`) rather
than searching for the literal URL.

```bash
witdl search "slime"
witdl search "crowned in a hundred days"
witdl search --download "https://witanime.you/anime/slime-..."
```

| Flag | Description |
|------|-------------|
| `--download`, `-d` | If the argument is a URL, download it instead of showing info |

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
witdl info "https://witanime.you/anime/tensei-shitara-slime-datta-ken-4th-season/"
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

Download anime episodes. Episodes already recorded as downloaded are skipped.

```bash
# Download specific episodes
witdl download "slime" --episodes 1-20
witdl download "crowned" --episodes 1,3,5,7-12

# Download from a URL
witdl download "https://witanime.you/anime/slime-..." --episodes 10-20

# Prefer a specific quality (falls back to any quality if unavailable)
witdl download "slime" --episodes 1-5 --quality hd
```

| Flag | Description |
|------|-------------|
| `--episodes`, `-e` | Episode range, e.g. `1-20`, `1,3,5`, `1-5,10,15-20` |
| `--quality`, `-q` | Prefer `fhd`, `hd`, or `sd` links |

**Episode range syntax:**

- `1-20` → episodes 1 through 20
- `1,3,5` → episodes 1, 3, and 5
- `1-5,10,15-20` → mixed ranges

---

### `witdl watch <anime...> [options]`

Auto-download new episodes as they release. Runs continuously until Ctrl+C.

```bash
witdl watch "slime datta ken 4th"
witdl watch "crowned in a hundred days" "slime datta ken 4th"
witdl watch "slime" -i 15     # check every 15 minutes
witdl watch "slime" -n        # notify only, don't download
```

| Flag | Description |
|------|-------------|
| `--interval`, `-i` | Check interval in minutes (default: 30) |
| `--no-download`, `-n` | Only notify about new episodes, don't download |

---

### `witdl list`

Show all downloaded anime in your library.

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

### `witdl queue`

Show pending downloads (anime with remaining or failed episodes).

### `witdl retry`

Retry all previously failed downloads.

### `witdl clean`

Remove failed download records from state.

---

### `witdl config <show|set|init>`

Manage configuration.

```bash
witdl config show
witdl config set download_dir /mnt/hdd/anime
witdl config set quality fhd
witdl config set max_concurrent_downloads 3
witdl config set hoster_priority mediafire,hexload,mp4upload
witdl config init
```

| Key | Default | Description |
|-----|---------|-------------|
| `download_dir` | `~/anime` | Where to save downloaded episodes |
| `quality` | `fhd` | Preferred quality: `fhd`, `hd`, `sd` |
| `hoster_priority` | `mediafire,hexload,mp4upload,gofile,workupload,wahmi` | Hoster try order |
| `max_concurrent_downloads` | `2` | How many episodes to download at once |
| `delay_between_episodes` | `2.0` | Seconds between episode requests |
| `timeout_per_download` | `900` | Max seconds per download (15 min) |
| `auto_retry` | `true` | Automatically retry failed downloads |
| `max_retries` | `3` | Number of retry attempts |

Config is saved at `~/.witdl/config.json`.

---

### `witdl --version`

```bash
witdl --version
# WitDL 0.1.0
```

## How It Works

### Download Pipeline

1. **Detect** — Find anime by name, anime URL, episode URL, or search URL
2. **Fetch episodes** — Decode the encrypted episode list from the anime page
3. **Decrypt links** — Reverse the XOR obfuscation on download URLs
4. **Resolve hoster** — Convert hoster page URLs into direct download links
5. **Download** — Use wget/curl with resume, retry, and concurrency
6. **Track** — Save download state to resume later

### Episode List Decoding

Modern WitAnime pages no longer embed episodes in the HTML. Instead the list is
delivered in an encrypted `processedEpisodeData` JavaScript variable composed of
two base64 blobs joined by a dot: `base64(XOR(json)) + "." + base64(key)`.
WitDL base64-decodes both, XORs the first with the second, and parses the
resulting JSON to recover each episode's number and **real URL**. Using the real
URL is what makes movies and specials (whose URLs omit a trailing number) work.

### Link Decryption

WitAnime obfuscates download links using XOR encryption with base64-encoded
keys. WitDL:

1. Extracts `_m.r` (XOR key), `_p0`–`_pN` (encrypted chunks), `_x` (reorder sequence)
2. XOR-decrypts each chunk with the key
3. Reorders chunks according to the sequence
4. Produces the final download URL

### ZIP Unwrapping

Some hosters deliver the video inside a ZIP archive. WitDL detects the ZIP magic
bytes, extracts the video, and renames it to the expected
`<anime>_EP<nn>.mp4` so it plays normally.

### Supported Hosters

Resolvers are implemented for these hosters:

| Hoster | Method |
|--------|--------|
| Mediafire | Direct download URL extraction |
| Hexload | AJAX API (`op=download3`) |
| Mp4upload | Embed page video URL extraction |
| Gofile | API (may require an account token) |

Hoster try order is controlled by `hoster_priority`. If a link fails, WitDL
falls back to the next one automatically.

## File Structure

```
witdl/
├── witdl/                    # Main package
│   ├── __init__.py           # Version info
│   ├── __main__.py           # `python3 -m witdl` entry point
│   ├── cli.py                # CLI with all subcommands
│   ├── config.py             # Config management
│   ├── downloader.py         # Download engine (concurrent, retry)
│   ├── library.py            # Library & state tracking
│   ├── models.py             # Data classes
│   ├── scraper.py            # WitAnime scraping & decryption
│   └── resolvers/            # Hoster resolvers
│       ├── __init__.py       # Resolver registry
│       ├── base.py           # Base resolver class
│       ├── mediafire.py      # Mediafire resolver
│       ├── hexload.py        # Hexload API resolver
│       ├── mp4upload.py      # Mp4upload embed resolver
│       └── gofile.py         # Gofile API resolver
├── tests/                    # unittest suite
├── docs/GUIDE.md             # In-depth usage & architecture guide
├── .github/                  # Issue/PR templates and CI
├── witdl.sh                  # Shell wrapper
├── pyproject.toml            # Package config
├── CHANGELOG.md              # Release history
├── CONTRIBUTING.md           # Contribution guide
├── CODE_OF_CONDUCT.md        # Community standards
├── SECURITY.md               # Security policy
├── LICENSE                   # MIT
└── README.md                 # This file
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

# Switch to an external drive
witdl config set download_dir /mnt/hdd/anime
```

## Development

```bash
pip install -e .
python -m unittest discover -s tests -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, conventions, and how to add a
hoster resolver. The full usage and architecture guide lives in
[docs/GUIDE.md](docs/GUIDE.md).

## Requirements

- Python 3.10+
- `wget` and/or `curl` (for downloads)
- No external Python packages (stdlib only)

## Community

- 🐛 [Report a bug](.github/ISSUE_TEMPLATE/bug_report.yml)
- 💡 [Request a feature](.github/ISSUE_TEMPLATE/feature_request.yml)
- 🔒 Report security issues privately — see [SECURITY.md](SECURITY.md)
- 📜 By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md)

## License

Released under the [MIT License](LICENSE). © 2026 Amanar Marouane.
