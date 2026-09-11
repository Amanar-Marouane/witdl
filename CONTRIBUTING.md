# Contributing to WitDL

Thanks for your interest in improving WitDL! This document explains how to set
up the project, the conventions we follow, and how to get your change merged.

By participating, you agree to abide by our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to contribute

- 🐛 Report bugs using the [bug report](.github/ISSUE_TEMPLATE/bug_report.yml) template
- 💡 Suggest features using the [feature request](.github/ISSUE_TEMPLATE/feature_request.yml) template
- 🧩 Add support for a new hoster (see below)
- 📝 Improve documentation
- 🧪 Add or improve tests

## Development setup

WitDL targets **Python 3.10+** and uses **only the standard library** — please
avoid adding runtime dependencies.

```bash
git clone https://github.com/Amanar-Marouane/witdl.git
cd witdl

# Editable install so the `witdl` command uses your checkout
pip install -e .
witdl --version
```

If you prefer not to install, you can run from the source tree:

```bash
python -m witdl --help
./witdl.sh --help
```

## Running tests

Tests use the standard-library `unittest` runner and do **not** require network
access.

```bash
python -m unittest discover -s tests -v
```

Please run the full suite before opening a pull request, and add tests for any
new behavior.

## Project layout

```
witdl/                    # The importable package
├── __init__.py           # Version info
├── __main__.py           # `python -m witdl` entry point
├── cli.py                # argparse subcommands and handlers
├── config.py             # ~/.witdl/config.json handling
├── downloader.py         # Download engine (wget/curl, retry, concurrency)
├── library.py            # ~/.witdl/state.json tracking
├── models.py             # Dataclasses and enums
├── scraper.py            # WitAnime scraping + decryption
└── resolvers/            # One module per supported hoster
tests/                    # unittest suite
docs/GUIDE.md             # In-depth usage and architecture guide
```

## Coding conventions

- **Standard library only.** Discuss before adding a dependency.
- Prefer small, focused functions and type hints on public functions.
- Keep the existing module boundaries: scraping in `scraper.py`, network
  downloads in `downloader.py`, hoster specifics in `resolvers/`.
- Formatting is conservative PEP 8; match the style of the surrounding code.
- Never commit secrets, tokens, or machine-specific paths.

## Adding a hoster resolver

1. Create `witdl/resolvers/<hoster>.py` subclassing `BaseResolver`.
2. Implement `resolve(self, url: str) -> str | None`, returning a direct
   download URL or `None` on failure.
3. Register it in the `RESOLVERS` dict in `witdl/resolvers/__init__.py`.
4. Add the hoster to the default `hoster_priority` in `witdl/config.py` if it
   should be tried by default.
5. Add tests and update the supported-hoster table in `README.md`.

## Commit messages

Write clear, imperative subject lines that explain *why* the change is made:

```
Add gofile resolver fallback for expired tokens
```

Keep each commit focused. Avoid mixing unrelated refactors with fixes.

## Pull request process

1. Fork the repository and create a topic branch off `main`.
2. Make your change, including tests and documentation updates.
3. Ensure `python -m unittest discover -s tests -v` passes.
4. Fill in the pull request template and link any related issues.
5. A maintainer will review; please be patient and responsive to feedback.

## Reporting security issues

Please do **not** open a public issue for security problems. See
[SECURITY.md](SECURITY.md) for how to report them privately.

## License

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
