#!/usr/bin/env python3
"""Miniflux backend for RSS deduplication."""
#
# Copyright (C) 2025 PR <code@reuteras.se>

try:
    import miniflux
except ImportError:
    miniflux = None


class MinifluxBackend:
    """Miniflux backend implementation using the official miniflux library."""

    def __init__(self, hostname, api_token):
        if miniflux is None:
            raise ImportError("miniflux library is required for Miniflux backend. Install with: pip install miniflux")
        self.hostname = hostname.rstrip("/")
        self.api_token = api_token
        self.client = None

    def login(self):
        """Authenticate with Miniflux."""
        self.client = miniflux.Client(self.hostname, api_key=self.api_token)
        # Test authentication
        try:
            self.client.me()
        except Exception as e:
            raise RuntimeError(f"Miniflux authentication failed: {e}") from e

    def get_feeds(self):
        """Get all feeds."""
        feeds = self.client.get_feeds()
        return [MinifluxFeed(feed) for feed in feeds]

    def get_categories(self):
        """Get all categories."""
        categories = self.client.get_categories()
        return [MinifluxCategory(cat) for cat in categories]

    def get_headlines(
        self, feed_id=None, view_mode="unread", since_id=None, limit=None, show_excerpt=False  # noqa: ARG002
    ):
        """Get entries/headlines."""
        # Note: show_excerpt parameter kept for API compatibility but not used in Miniflux
        kwargs = {}

        if view_mode == "unread":
            kwargs["status"] = "unread"
        elif view_mode == "all_articles":
            # Use tuple for repeatable query parameters (status=read&status=unread)
            kwargs["status"] = ("read", "unread")

        if since_id:
            kwargs["after_entry_id"] = since_id

        if limit:
            kwargs["limit"] = limit

        if feed_id and feed_id != -1:
            kwargs["feed_id"] = feed_id

        response = self.client.get_entries(**kwargs)
        # get_entries returns a dict with "entries" key
        entries = response.get("entries", []) if isinstance(response, dict) else response
        return [MinifluxArticle(entry) for entry in entries]

    def get_unread_count(self):
        """Get total unread count."""
        response = self.client.get_entries(status="unread", limit=1)
        # get_entries returns a dict with "total" key containing total count
        return response.get("total", 0) if isinstance(response, dict) else 0

    def mark_read(self, article_id):
        """Mark an article as read."""
        self.client.update_entries([article_id], status="read")

    def mark_starred(self, article_id):
        """Star/bookmark an article."""
        self.client.toggle_bookmark(article_id)

    def toggle_starred(self, article_id):
        """Toggle star/bookmark status."""
        self.client.toggle_bookmark(article_id)


class MinifluxFeed:
    """Wrapper for Miniflux feed data."""

    def __init__(self, feed_data):
        self.id = feed_data["id"]
        self.title = feed_data["title"]
        self.feed_url = feed_data.get("feed_url", "")
        self.site_url = feed_data.get("site_url", "")
        self.category_id = feed_data.get("category", {}).get("id")

    def headlines(self, view_mode="unread", since_id=None, limit=None):
        """Not implemented - use backend.get_headlines instead."""
        raise NotImplementedError("Use backend.get_headlines with feed_id parameter instead")


class MinifluxCategory:
    """Wrapper for Miniflux category data."""

    def __init__(self, category_data):
        self.id = category_data["id"]
        self.title = category_data["title"]


class MinifluxArticle:
    """Wrapper for Miniflux entry data."""

    def __init__(self, entry_data):
        self.id = entry_data["id"]
        self.title = entry_data["title"]
        self.link = entry_data.get("url", "")
        self.feed_id = entry_data.get("feed", {}).get("id")
        self.feed_title = entry_data.get("feed", {}).get("title", "Unknown")
        self.unread = entry_data.get("status") == "unread"
        self.is_updated = entry_data.get("changed_at") != entry_data.get("published_at")


def create_backend(config):
    """Create Miniflux backend from configuration."""
    hostname = config.get("miniflux", "hostname")
    api_token = config.get("miniflux", "api_token")
    backend = MinifluxBackend(hostname, api_token)
    backend.login()
    return backend
