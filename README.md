# newsdedup

[![Lint Code Base v4](https://github.com/reuteras/newsdedup/actions/workflows/linter.yml/badge.svg)](https://github.com/reuteras/newsdedup/actions/workflows/linter.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)


A project to deduplicate my news feed.

For a long time I've added a lot of RSS feeds and now I've ended up with a lot
of duplicate entries for big stories. With this project I aim to move duplicates
to starred and mark them as read. This might change in the future if I find a
better way to do it.

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. To install uv:

    curl -LsSf https://astral.sh/uv/install.sh | sh

Then install the project dependencies:

    make sync

Or directly with uv:

    uv sync

## Usage

To run the code as a daemon under systemd you can do the following steps:

    mkdir -p ~/.config/systemd/user/
    cp newsdedup.service.default ~/.config/systemd/user/newsdedup.service
    systemctl --user enable newsdedup.service
    systemctl --user start newsdedup.service

To watch the logs you can run:

    journalctl -f --user-unit newsdedup

Unmark stared articles from the command-line with:

    uv run unstar -b

List all feeds:

    uv run list-feeds

Run newsdedup directly:

    uv run newsdedup newsdedup.cfg

## Features

### Multiple Backend Support

newsdedup now supports two RSS reader backends:
- **Tiny Tiny RSS** (default) - The original backend
- **Miniflux** - Modern, minimalist RSS reader

To switch backends, edit your `newsdedup.cfg` file:

    [newsdedup]
    backend=miniflux  # or ttrss

### Enhanced Duplicate Detection

The duplicate detection has been significantly improved with:

1.  **Multiple Similarity Algorithms**:
    -   `token_sort` - Token-based sorting comparison (original)
    -   `token_set` - Set-based token comparison
    -   `partial` - Partial string matching
    -   `jaccard` - Jaccard similarity coefficient
    -   `combined` - Uses the best result from multiple methods (recommended)

2.  **URL-based Deduplication**:
    -   Detects duplicate articles by normalized URLs
    -   Removes tracking parameters automatically
    -   Can be disabled in configuration

Configure in `newsdedup.cfg`:

    [newsdedup]
    similarity_method=combined  # Choose your similarity algorithm
    check_urls=true            # Enable URL-based deduplication

### Configuration

See `newsdedup.cfg.default` for a complete configuration example supporting both backends.

For **Miniflux**:
1. Generate an API token in Miniflux Settings > API Keys
2. Add to your config:

        [miniflux]
        hostname=https://miniflux.example.org
        api_token=your-api-token-here

## Links

Some of the relevant API:s used in this project.

* [ttrss-python](http://ttrss-python.readthedocs.org/en/latest/)
* [Tiny Tiny RSS - API Reference](https://tt-rss.org/wiki/ApiReference)
* [Miniflux - API Documentation](https://miniflux.app/docs/api.html)
* [fuzzywuzzy](https://github.com/seatgeek/fuzzywuzzy)
