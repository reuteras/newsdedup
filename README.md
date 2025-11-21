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

## Configuration

Create a `newsdedup.toml` file in your project directory. Use `newsdedup.toml.example` as a template:

    cp newsdedup.toml.example newsdedup.toml
    # Edit newsdedup.toml with your Miniflux settings

For **Miniflux**:
1. Generate an API token in Miniflux Settings > API Keys
2. Add to your `newsdedup.toml`:

        [miniflux]
        hostname = "https://miniflux.example.com"
        api_token = "your-api-token-here"

## Usage

### Command Line

Run newsdedup once to check for duplicates:

    uv run newsdedup

Run with debug output:

    uv run newsdedup --debug

Preview changes without marking articles (dry-run mode):

    uv run newsdedup --dry-run

### Daemon Mode (Continuous Operation)

Run newsdedup continuously with systemd:

    mkdir -p ~/.config/systemd/user/
    cp newsdedup.service ~/.config/systemd/user/newsdedup.service

Edit the service file to point to your configuration file location if needed:

    systemctl --user daemon-reload
    systemctl --user enable newsdedup.service
    systemctl --user start newsdedup.service

To watch the logs:

    journalctl -f --user-unit newsdedup

To stop the service:

    systemctl --user stop newsdedup.service

To check the service status:

    systemctl --user status newsdedup.service

## Features

### Miniflux Integration

newsdedup is designed for [Miniflux](https://miniflux.app/) - a modern, minimalist RSS reader. It uses the official Miniflux API to detect and manage duplicate articles.

### Intelligent Duplicate Detection

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

Configure in `newsdedup.toml`:

    [newsdedup]
    similarity_method = "combined"  # Choose: token_sort, token_set, jaccard, or combined
    check_urls = true              # Enable URL-based deduplication
    ratio = 80                      # Similarity threshold (0-100)
    maxcount = 50                   # Max articles to learn per feed
    sleep = 60                      # Sleep time between checks in daemon mode
    learning_retry_interval = 10    # Force re-learning every N iterations

## Links

Relevant APIs and libraries used in this project:

* [Miniflux - Official Documentation](https://miniflux.app/)
* [Miniflux - API Reference](https://miniflux.app/docs/api.html)
* [miniflux-python - Python Client Library](https://github.com/miniflux/python-client)
* [fuzzywuzzy - Fuzzy String Matching](https://github.com/seatgeek/fuzzywuzzy)
* [uv - Python Package Manager](https://docs.astral.sh/uv/)
