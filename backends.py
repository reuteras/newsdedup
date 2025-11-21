#!/usr/bin/env python3
"""Backend abstraction layer for different RSS readers."""
#
# Copyright (C) 2025 PR <code@reuteras.se>

from abc import ABC, abstractmethod

import requests
from ttrss.client import TTRClient
from ttrss.exceptions import TTRApiDisabled, TTRAuthFailure, TTRNotLoggedIn

try:
    import miniflux
except ImportError:
    miniflux = None

# Constants
HTTP_OK = 200


class Article:
    """Generic article representation."""

    def __init__(  # noqa: PLR0913
        self,
        article_id,
        title,
        link,
        feed_id,
        feed_title,
        unread=False,
        is_updated=False,
    ):
        self.id = article_id
        self.title = title
        self.link = link
        self.feed_id = feed_id
        self.feed_title = feed_title
        self.unread = unread
        self.is_updated = is_updated


class RSSBackend(ABC):
    """Abstract base class for RSS backend implementations."""

    @abstractmethod
    def login(self):
        """Authenticate with the RSS service."""

    @abstractmethod
    def get_feeds(self):
        """Get all feeds."""

    @abstractmethod
    def get_headlines(self, feed_id=None, view_mode="unread", since_id=None, limit=None):
        """Get headlines/entries."""

    @abstractmethod
    def get_unread_count(self):
        """Get total unread count."""

    @abstractmethod
    def mark_read(self, article_id):
        """Mark an article as read."""

    @abstractmethod
    def mark_starred(self, article_id):
        """Star/bookmark an article."""

    @abstractmethod
    def toggle_starred(self, article_id):
        """Toggle star/bookmark status."""


class TTRSSBackend(RSSBackend):
    """Tiny Tiny RSS backend implementation."""

    def __init__(self, hostname, username, password):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.client = None

    def login(self):
        """Authenticate with Tiny Tiny RSS."""
        try:
            self.client = TTRClient(self.hostname, self.username, self.password, auto_login=False)
            self.client.login()
        except (TTRApiDisabled, TTRNotLoggedIn, TTRAuthFailure) as error:
            raise RuntimeError(f"Couldn't setup TTRClient: {error}") from error

    def get_feeds(self):
        """Get all feeds."""
        return self.client.get_feeds()

    def get_categories(self):
        """Get all categories."""
        return self.client.get_categories()

    def get_headlines(
        self, feed_id=None, view_mode="unread", since_id=None, limit=None, show_excerpt=False
    ):
        """Get headlines."""
        return self.client.get_headlines(
            feed_id=feed_id,
            view_mode=view_mode,
            since_id=since_id,
            limit=limit,
            show_excerpt=show_excerpt,
        )

    def get_unread_count(self):
        """Get total unread count."""
        return self.client.get_unread_count()

    def mark_read(self, article_id):
        """Mark an article as read."""
        self.client.mark_read(article_id)

    def mark_starred(self, article_id):
        """Star an article."""
        self.client.mark_starred(article_id)

    def toggle_starred(self, article_id):
        """Toggle starred status."""
        self.client.toggle_starred(article_id)


class MinifluxBackend(RSSBackend):
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
            kwargs["status"] = ["read", "unread"]

        if since_id:
            kwargs["after_entry_id"] = since_id

        if limit:
            kwargs["limit"] = limit

        if feed_id and feed_id != -1:
            kwargs["feed_id"] = feed_id

        entries = self.client.get_entries(**kwargs)
        return [MinifluxArticle(entry) for entry in entries]

    def get_unread_count(self):
        """Get total unread count."""
        entries = self.client.get_entries(status="unread", limit=1)
        # The client returns a list, check if there's a total_unread in the response metadata
        # Fallback: count the unread entries manually
        all_unread = self.client.get_entries(status="unread", limit=1000)
        return len(all_unread) if all_unread else 0

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


def create_backend(backend_type, config):
    """Factory function to create appropriate backend."""
    if backend_type == "ttrss":
        hostname = config.get("ttrss", "hostname")
        username = config.get("ttrss", "username")
        password = config.get("ttrss", "password")
        backend = TTRSSBackend(hostname, username, password)
    elif backend_type == "miniflux":
        hostname = config.get("miniflux", "hostname")
        api_token = config.get("miniflux", "api_token")
        backend = MinifluxBackend(hostname, api_token)
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")

    backend.login()
    return backend
