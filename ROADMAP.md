# Roadmap

This roadmap tracks what WitDL has shipped and what we plan to build next. It is
a living document — items are **not** commitments, and priorities may change
based on feedback. To propose an idea, open a
[feature request](.github/ISSUE_TEMPLATE/feature_request.yml).

**Legend:** ✅ shipped · 🚧 in progress · 📋 planned · 💡 exploring

## Shipped — v0.1.0

### Core engine

- [x] ✅ Multi-hoster download with automatic fallback
- [x] ✅ Resume support (`wget -c` / `curl -C -`)
- [x] ✅ Retry with exponential backoff
- [x] ✅ Concurrent episode downloads (`max_concurrent_downloads`)
- [x] ✅ Download-link decryption
- [x] ✅ Encrypted episode-list (`processedEpisodeData`) decoding
- [x] ✅ Movie / special episode URL handling
- [x] ✅ ZIP-wrapped download extraction
- [x] ✅ Quality preference (`fhd` / `hd` / `sd`) with fallback

### Hoster resolvers

- [x] ✅ Mediafire
- [x] ✅ Hexload
- [x] ✅ Mp4upload
- [x] ✅ Gofile

### CLI

- [x] ✅ `search` with URL detection and `--download`
- [x] ✅ `info`, `download`, `list`, `missing`, `queue`, `retry`, `clean`
- [x] ✅ `watch` for automatic new-episode downloads
- [x] ✅ `config show|set|init`
- [x] ✅ `--version`

### Library and configuration

- [x] ✅ Library state persisted to `~/.witdl/state.json`
- [x] ✅ Configuration persisted to `~/.witdl/config.json`

### Project and community

- [x] ✅ MIT license
- [x] ✅ README and in-depth [usage guide](docs/GUIDE.md)
- [x] ✅ CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, CHANGELOG
- [x] ✅ GitHub issue and pull request templates
- [x] ✅ CI running the test suite on Python 3.10–3.13
- [x] ✅ Offline test suite (82 tests)

## Next — v0.1.x (polish and hardening)

- [ ] 🚧 Single-source the version to avoid drift between `witdl/__init__.py` and
      `pyproject.toml`
- [ ] 📋 Add `py.typed` (PEP 561) so downstream users get the type hints
- [ ] 📋 Add linting and formatting (Ruff) with a CI lint job
- [ ] 📋 Add test coverage reporting to CI
- [ ] 📋 Verify sdist/wheel build and metadata in CI
- [ ] 📋 Add a PyPI release workflow triggered by version tags
- [ ] 📋 Expand offline tests for scraper decoding and hoster resolvers
- [ ] 📋 Add structured logging and a `--verbose` flag
- [ ] 📋 Add a code-formatting and line-ending `.editorconfig` / `.gitattributes`
- [ ] 📋 Enable Dependabot for GitHub Actions updates

## Planned — v0.2.0 and beyond

- [ ] 📋 Pluggable third-party hoster resolvers
- [ ] 📋 Subtitle download and embedding
- [ ] 📋 Anime metadata enrichment (AniList / MyAnimeList)
- [ ] 📋 Segmented / parallel downloading for large files
- [ ] 📋 Notifications (desktop / webhook) when `watch` finds new episodes
- [ ] 📋 Docker image and `docker-compose` example
- [ ] 📋 Interactive TUI
- [ ] 💡 Support for additional sites
- [ ] 💡 Internationalization of CLI output
- [ ] 💡 Reading a queue/batch file for unattended runs

## Known limitations

- The scraper depends on WitAnime's HTML/JS structure; upstream changes can break
  scraping until a parser or resolver is updated.
- WitAnime is the only supported site today.
- Gofile links may require an account token and can fail without one.
- `--quality` falls back to any available quality when the requested one is
  missing.
- `witdl watch` polls a fixed episode range and is unaware of season boundaries.
- Downloads require `wget` and/or `curl`; Windows support is untested.
- Tests are offline by design, so live site changes are not caught by CI.

## How to help

- Pick an item above and open a pull request — see [CONTRIBUTING.md](CONTRIBUTING.md).
- Propose new items with the feature-request template.
