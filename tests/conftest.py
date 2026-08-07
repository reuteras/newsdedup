"""Shared fixtures for newsdedup tests."""

import argparse

import pytest


class Article:
    """Minimal stand-in for a Miniflux article/headline."""

    def __init__(self, title, feed_title="Feed", feed_id=1, link="", article_id=1, unread=True):
        self.title = title
        self.feed_title = feed_title
        self.feed_id = feed_id
        self.link = link
        self.id = article_id
        self.unread = unread


@pytest.fixture
def make_article():
    return Article


@pytest.fixture
def make_args():
    def _make(**overrides):
        defaults = {"debug": False, "verbose": False, "daemon": False, "dry_run": False}
        defaults.update(overrides)
        return argparse.Namespace(**defaults)

    return _make
