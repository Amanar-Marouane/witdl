# 🎬 WitDL — Advanced WitAnime Downloader

Download anime from [WitAnime](https://witanime.you) with search, multi-hoster support, resume, and library management.

## Features

- 🔍 **Search** — Find anime directly from the terminal
- 📥 **Smart Downloads** — Auto-fallback between hosters (mediafire, hexload, mp4upload, gofile)
- ⏯️ **Resume** — Partial downloads resume automatically
- 🔄 **Retry** — Failed downloads retry with exponential backoff
- 📚 **Library** — Track what's downloaded, find missing episodes
- ⚙️ **Configurable** — Quality, hoster priority, download dir, and more

## Install

```bash
cd witdl
pip install -e .
```

Or run directly without install:

```bash
python -m witdl.cli <command>
```

## Quick Start

```bash
# Search for an anime
witdl search "slime datta ken"

# Download episodes 10-20
witdl download "slime datta ken 4th" --episodes 10-20

# Download from URL
witdl download https://witanime.you/anime/tensei-shitara-slime-datta-ken-4th-season-الحلقة-20/ --episodes 1-20

# Check your library
witdl list

# Find missing episodes
witdl missing "slime datta ken 4th"

# Retry failed downloads
witdl retry
```

## Commands

| Command | Description |
|---------|-------------|
| `witdl search <query>` | Search for anime on WitAnime |
| `witdl info <url/query>` | Show anime details |
| `witdl download <url/query>` | Download episodes |
| `witdl list` | List downloaded anime |
| `witdl missing <url/query>` | Show missing episodes |
| `witdl queue` | Show download queue |
| `witdl retry` | Retry failed downloads |
| `witdl clean` | Clean failed records |
| `witdl config show` | Show configuration |
| `witdl config set <key> <value>` | Set config value |
| `witdl config init` | Interactive setup |

## Configuration

Config is saved at `~/.witdl/config.json`.

```bash
# Set download directory
witdl config set download_dir /mnt/hdd/anime

# Set quality preference
witdl config set quality fhd

# Set hoster priority (comma-separated)
witdl config set hoster_priority mediafire,hexload,mp4upload,gofile

# Set delay between episodes (seconds)
witdl config set delay_between_episodes 2

# Interactive setup
witdl config init
```

### Default Config

```json
{
  "download_dir": "~/anime",
  "quality": "fhd",
  "hoster_priority": ["mediafire", "hexload", "mp4upload", "gofile", "workupload", "wahmi"],
  "max_concurrent_downloads": 2,
  "delay_between_episodes": 2.0,
  "timeout_per_download": 900,
  "auto_retry": true,
  "max_retries": 3
}
```

## Download Format

Files are saved as:

```
~/anime/
├── Crowned in a Hundred Days/
│   ├── crowned_EP01.mp4
│   ├── crowned_EP02.mp4
│   └── ...
└── Tensei shitara Slime Datta Ken 4th Season/
    ├── tensei_EP10.mp4
    └── ...
```

## Requirements

- Python 3.10+
- `wget` and/or `curl` (for downloads)
- No external Python packages needed (stdlib only)

## License

MIT
