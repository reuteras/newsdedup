#!/usr/bin/env python3
"""Backend abstraction layer for different RSS readers."""
#
# Copyright (C) 2025 PR <code@reuteras.se>

from abc import ABC, abstractmethod

import requests
from ttrss.client import TTRClient
from ttrss.exceptions import TTRApiDisabled, TTRAuthFailure, TTRNotLoggedIn

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
    """Miniflux backend implementation."""

    def __init__(self, hostname, api_token):
        self.hostname = hostname.rstrip("/")
        self.api_token = api_token
        self.session = None

    def login(self):
        """Authenticate with Miniflux."""
        self.session = requests.Session()
        self.session.headers.update({"X-Auth-Token": self.api_token})

        # Test authentication
        response = self.session.get(f"{self.hostname}/v1/me", timeout=10)
        if response.status_code != HTTP_OK:
            raise RuntimeError(f"Miniflux authentication failed: {response.status_code}")

    def get_feeds(self):
        """Get all feeds."""
        response = self.session.get(f"{self.hostname}/v1/feeds", timeout=10)
        response.raise_for_status()
        return [MinifluxFeed(feed) for feed in response.json()]

    def get_categories(self):
        """Get all categories."""
        response = self.session.get(f"{self.hostname}/v1/categories", timeout=10)
        response.raise_for_status()
        return [MinifluxCategory(cat) for cat in response.json()]

    def get_headlines(
        self, feed_id=None, view_mode="unread", since_id=None, limit=None, show_excerpt=False  # noqa: ARG002
    ):
        """Get entries/headlines."""
        # Note: show_excerpt parameter kept for API compatibility but not used in Miniflux
        params = {}

        if view_mode == "unread":
            params["status"] = "unread"
        elif view_mode == "all_articles":
            params["status"] = "read,unread"

        if since_id:
            params["after_entry_id"] = since_id

        if limit:
            params["limit"] = limit

        if feed_id and feed_id != -1:
            params["feed_id"] = feed_id

        response = self.session.get(f"{self.hostname}/v1/entries", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        return [MinifluxArticle(entry) for entry in data.get("entries", [])]

    def get_unread_count(self):
        """Get total unread count."""
        response = self.session.get(f"{self.hostname}/v1/entries?status=unread&limit=1", timeout=10)
        response.raise_for_status()
        return response.json().get("total", 0)

    def mark_read(self, article_id):
        """Mark an article as read."""
        response = self.session.put(
            f"{self.hostname}/v1/entries",
            json={"entry_ids": [article_id], "status": "read"},
            timeout=10,
        )
        response.raise_for_status()

    def mark_starred(self, article_id):
        """Star/bookmark an article."""
        response = self.session.put(f"{self.hostname}/v1/entries/{article_id}/bookmark", timeout=10)
        response.raise_for_status()

    def toggle_starred(self, article_id):
        """Toggle star/bookmark status."""
        # Miniflux uses PUT to toggle bookmark
        response = self.session.put(f"{self.hostname}/v1/entries/{article_id}/bookmark", timeout=10)
        response.raise_for_status()


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
