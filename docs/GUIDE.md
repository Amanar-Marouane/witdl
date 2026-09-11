# WitDL Guide

This guide covers installation, day-to-day usage, how WitDL works under the
hood, and how to troubleshoot common problems. For a quick overview, see the
[README](../README.md).

## Contents

- [Installation](#installation)
- [Requirements](#requirements)
- [Configuration](#configuration)
- [Accepted inputs](#accepted-inputs)
- [Commands](#commands)
- [How it works](#how-it-works)
- [Supported hosters](#supported-hosts)
- [Troubleshooting](#troubleshooting)
- [Legal and ethical use](#legal-and-ethical-use)

## Installation

WitDL is a pure-Python package with no runtime dependencies.

### From source (recommended while pre-1.0)

```bash
git clone https://github.com/OWNER/witdl.git
cd witdl
pip install -e .
witdl --version
```

### Without installing

Run straight from the checkout:

```bash
python -m witdl --help
```

Or use the bundled wrapper, which only needs the repository on disk:

```bash
./witdl.sh --help
```

To expose the wrapper globally:

```bash
ln -sf "$(pwd)/witdl.sh" ~/.local/bin/witdl
witdl --version
```

## Requirements

- **Python 3.10 or newer**
- **`wget` and/or `curl`** for the download step (WitDL tries `wget` first, then
  `curl`)
- A POSIX-like shell if you use `witdl.sh`

## Configuration

WitDL stores its configuration at `~/.witdl/config.json` and its download
history at `~/.witdl/state.json`.

```bash
witdl config show                      # print current values
witdl config set quality hd            # change a value
witdl config set download_dir /mnt/anime
witdl config init                      # interactive setup
```

| Key | Default | Description |
| --- | --- | --- |
| `download_dir` | `~/anime` | Where episodes are saved |
| `quality` | `fhd` | Preferred quality: `fhd`, `hd`, `sd` |
| `hoster_priority` | `mediafire,hexload,mp4upload,gofile,workupload,wahmi` | Hoster order to try |
| `max_concurrent_downloads` | `2` | Episodes downloaded at once |
| `delay_between_episodes` | `2.0` | Seconds to wait between episode requests |
| `timeout_per_download` | `900` | Max seconds per download |
| `auto_retry` | `true` | Retry failed downloads automatically |
| `max_retries` | `3` | Retry attempts per episode |
| `user_agent` | Chrome UA string | User agent sent with requests |

## Accepted inputs

Most commands accept a **search query**, an **anime URL**, an **episode URL**, or
a **search-results URL**:

```bash
witdl download "slime datta ken 4th"
witdl download https://witanime.you/anime/tensei-shitara-slime-datta-ken-4th-season/
witdl download https://witanime.you/episode/film-the-ribbon-hero/
witdl download "https://witanime.you/?search_param=animes&s=slime"
```

URLs without a scheme (for example `witanime.you/anime/foo/`) are normalized
automatically.

## Commands

### `witdl search <query|url>`

Search for anime. If the argument is a URL, WitDL recognizes it and shows the
anime's info instead of searching for the literal URL string.

```bash
witdl search "slime"
witdl search --download "https://witanime.you/anime/tensei-shitara-slime-datta-ken-4th-season/"
```

Flags:

| Flag | Description |
| --- | --- |
| `--download`, `-d` | If the argument is a URL, download it instead of showing info |

### `witdl info <query|url>`

Print the anime name, slug, episode count, and available episode numbers.

```bash
witdl info "slime datta ken 4th"
```

### `witdl download <query|url> [options]`

Download episodes. Episodes already recorded as downloaded are skipped.

```bash
witdl download "slime" --episodes 1-20
witdl download "crowned" --episodes 1,3,5,7-12
witdl download "slime" --episodes 1-5 --quality hd
```

Flags:

| Flag | Description |
| --- | --- |
| `--episodes`, `-e` | Episode range, e.g. `1-20`, `1,3,5`, `1-5,10,15-20` |
| `--quality`, `-q` | Prefer `fhd`, `hd`, or `sd` links (falls back to any quality if unavailable) |

### `witdl watch <anime...> [options]`

Poll for new episodes and download them as they appear. Runs until stopped with
Ctrl+C.

```bash
witdl watch "slime datta ken 4th"
witdl watch "crowned" "slime" -i 15
witdl watch "slime" -n          # notify only, do not download
```

| Flag | Description |
| --- | --- |
| `--interval`, `-i` | Minutes between checks (default: 30) |
| `--no-download`, `-n` | Report new episodes without downloading |

### `witdl list`

List everything in the local library with progress counts.

### `witdl missing <query|url>`

Show which episodes have not been downloaded yet.

### `witdl queue`

Show anime with remaining or failed episodes.

### `witdl retry`

Retry episodes previously recorded as failed.

### `witdl clean`

Remove failed download records from the state file.

### `witdl config <show|set|init>`

Read or write configuration values (see [Configuration](#configuration)).

### `witdl --version`

Print the installed version.

## How it works

WitDL follows a five-stage pipeline:

1. **Detect** — Resolve the input to an anime. Search queries hit the site's
   search endpoint; anime, episode, and search-result URLs are followed to the
   parent anime page.
2. **Fetch episode list** — Modern WitAnime pages do not embed the episode list
   in HTML. Instead the list is delivered in an encrypted `processedEpisodeData`
   JavaScript variable, which WitDL decodes (see below).
3. **Decrypt links** — Each episode page hides its download URLs behind an XOR
   scheme that WitDL reverses.
4. **Resolve hoster** — The hoster page URL is converted into a direct download
   URL by the matching resolver.
5. **Download & track** — `wget` (then `curl`) downloads with resume support;
   the result is written to `~/.witdl/state.json`.

### Episode-list decoding

The `processedEpisodeData` variable is two base64 blobs joined by a dot:

```
processedEpisodeData = base64(XOR_encrypted_json) + "." + base64(key)
```

WitDL base64-decodes both parts, XORs the first with the second, and parses the
result as JSON. Each entry carries the episode `number`, its real `url`, `type`,
and a `screenshot`. Using the real URL (rather than guessing one from the slug)
is what makes movies and specials work, since their URLs do not follow the
numeric episode pattern.

### Download-link decryption

Episode pages obfuscate download links with XOR encryption:

1. Extract `_m.r` (base64 XOR key), `_p0`–`_pN` (encrypted chunks), and `_x`
   (the chunk ordering sequence).
2. XOR-decrypt each chunk with the key.
3. Reorder the chunks according to `_x`.
4. Join them into the final URL.

### ZIP-wrapped downloads

Some hosters deliver the video inside a ZIP archive rather than as a raw media
file. WitDL detects the ZIP magic bytes, extracts the video, and renames it to
the expected `<anime>_EP<nn>.mp4`, so the saved file plays normally.

## Supported hosts

Resolvers are implemented for the following hosters:

| Hoster | Method |
| --- | --- |
| Mediafire | Direct download URL extraction |
| Hexload | AJAX API (`op=download3`) |
| Mp4upload | Embed page video URL extraction |
| Gofile | API (may require an account token) |

Additional hosters listed in `hoster_priority` (for example `workupload` and
`wahmi`) are only attempted if a resolver exists for them; otherwise WitDL falls
back to the next link. Hosters are tried in `hoster_priority` order, and WitDL
falls back automatically when one fails.

## Troubleshooting

**A downloaded file won't play / keeps its `.mp4` name but is a ZIP.**
Older downloads may have been saved before ZIP extraction was added. Re-run the
download, or extract the archive manually — the real video is inside.

**"No download links found" for an episode.**
The hoster may be unavailable or the episode may not have links yet. Try
`witdl retry`, or select a different hoster order with
`witdl config set hoster_priority ...`.

**Episodes show as 0 or an episode 404s.**
Make sure you are on the latest version — WitAnime changed how episode lists are
served, and older builds could not read them.

**The site blocks requests or returns an error page.**
Increase `delay_between_episodes`, lower `max_concurrent_downloads`, or set a
different `user_agent`. Please be considerate and avoid hammering the site.

**Downloads fail with a resolver error.**
Run `witdl retry`; if it keeps failing, the hoster's page structure may have
changed and the resolver may need updating.

## Legal and ethical use

WitDL is a tool for downloading media from WitAnime. It does not host or
distribute any content. You are responsible for ensuring your use complies with
applicable copyright law and the terms of service of the sites and hosters you
access. Do not use WitDL to download material you do not have the right to.
