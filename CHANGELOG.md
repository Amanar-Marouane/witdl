# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `witdl search` now detects URLs and routes them to `info`, with a
  `--download`/`-d` flag to download directly instead.
- Quality selection: `--quality/-q` and the `quality` config key now filter
  download links to the requested quality when available.

### Fixed

- Anime pages whose episode list is delivered via the encrypted
  `processedEpisodeData` JavaScript variable now parse correctly, restoring
  episode discovery.
- Movies and specials whose episode URLs use `فيلم` (or omit a trailing number)
  are now resolved by following the parent anime link instead of constructing a
  404 URL.
- Hoster responses that wrap the video in a ZIP archive are now detected and
  extracted automatically, so downloaded files play correctly instead of being
  saved as unplayable ZIPs with an `.mp4` extension.
- Scheme-less URLs (for example `witanime.you/anime/foo/`) are normalized before
  fetching.

## [0.1.0] - 2026

### Added

- Core downloader with multi-hoster fallback, resume, and retry with backoff.
- Concurrent episode downloads via a thread pool.
- Obfuscated download-link decryption.
- CLI commands: `search`, `info`, `download`, `watch`, `list`, `missing`,
  `queue`, `retry`, `clean`, and `config`.
- Library and download-state tracking persisted to `~/.witdl/state.json`.
- Configuration via `~/.witdl/config.json`.
- `witdl.sh` shell wrapper and `pip install -e .` packaging.
- Comprehensive `unittest` suite.

[Unreleased]: https://github.com/Amanar-Marouane/witdl/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Amanar-Marouane/witdl/releases/tag/v0.1.0
