#!/usr/bin/env python3
"""News deduplication for Miniflux RSS reader."""
#
# Copyright (C) 2015-2025 PR <code@reuteras.se>

import argparse
import logging
import re
import sys
import time
import tomllib
from collections import deque
from pathlib import Path

from fuzzywuzzy import fuzz

from backends import create_backend

# Constants
DEFAULT_BATCH_SIZE = 200
HTTP_OK = 200


class LearnedArticle:
    """Store metadata about learned articles for comparison."""

    def __init__(self, title, url, feed_id):
        """Initialize learned article."""
        self.title = title
        self.url = url
        self.feed_id = feed_id


def read_configuration(config_file):
    """Read TOML configuration file."""
    config_path = Path(config_file)
    if not config_path.exists():
        print(f"Configuration file not found: {config_file}", flush=True)
        sys.exit(1)

    try:
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
    except Exception as e:
        print(f"Error reading configuration file: {e}", flush=True)
        sys.exit(1)

    if not config:
        print("Configuration file is empty.", flush=True)
        sys.exit(1)

    return config


def load_state(state_file=".newsdedup_state"):
    """Load the last processed article ID from state file."""
    state_path = Path(state_file)
    if state_path.exists():
        try:
            with open(state_path) as f:
                last_id = int(f.read().strip())
                return last_id
        except Exception:  # pylint: disable=broad-except
            pass
    return 0


def save_state(last_id, state_file=".newsdedup_state"):
    """Save the last processed article ID to state file."""
    try:
        with open(state_file, "w") as f:
            f.write(str(last_id))
    except Exception as e:  # pylint: disable=broad-except
        print(f"Warning: Could not save state: {e}", flush=True)


def init_backend(config):
    """Initialize Miniflux RSS backend."""
    try:
        return create_backend(config)
    except Exception as error:  # pylint: disable=broad-except
        print(f"Could not initialize Miniflux backend: {error}", flush=True)
        sys.exit(1)


def init_title_queue(config):
    """Init deque queue to store handled titles."""
    # maxcount is per-feed, estimate total as maxcount * 100 feeds or minimum of 5000
    maxcount_per_feed = int(config.get("newsdedup", {}).get("maxcount", 50))
    total_maxlen = max(5000, maxcount_per_feed * 100)
    return deque(maxlen=total_maxlen)


def init_url_queue(config):
    """Init deque queue to store handled URLs."""
    # Same as title queue - bounded to prevent unbounded growth
    maxcount_per_feed = int(config.get("newsdedup", {}).get("maxcount", 50))
    total_maxlen = max(5000, maxcount_per_feed * 100)
    return deque(maxlen=total_maxlen)


def normalize_url(url):
    """Normalize URL by removing tracking parameters and fragments."""
    # Remove common tracking parameters
    tracking_params = [
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
        "msclkid",
        "mc_cid",
        "mc_eid",
    ]

    # Remove fragment
    url_without_fragment = url.split("#")[0]

    # Remove tracking parameters
    for param in tracking_params:
        url_without_fragment = re.sub(rf"[?&]{param}=[^&]*", "", url_without_fragment)

    # Clean up any trailing ? or &
    return re.sub(r"[?&]$", "", url_without_fragment)


def jaccard_similarity(str1, str2):
    """Calculate Jaccard similarity between two strings."""
    words1 = set(str1.lower().split())
    words2 = set(str2.lower().split())

    if not words1 or not words2:
        return 0

    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))

    return int((intersection / union) * 100) if union > 0 else 0


def calculate_similarity(title1, title2, method="token_sort"):
    """Calculate similarity between two titles using the specified method."""
    if method == "token_sort":
        return fuzz.token_sort_ratio(title1, title2)
    if method == "token_set":
        return fuzz.token_set_ratio(title1, title2)
    if method == "partial":
        return fuzz.partial_ratio(title1, title2)
    if method == "jaccard":
        return jaccard_similarity(title1, title2)
    if method == "combined":
        # Use a combination of methods for better accuracy
        token_sort = fuzz.token_sort_ratio(title1, title2)
        token_set = fuzz.token_set_ratio(title1, title2)
        jaccard = jaccard_similarity(title1, title2)
        return max(token_sort, token_set, jaccard)
    return fuzz.token_sort_ratio(title1, title2)


def learn_last_read(
    rss, title_queue, url_queue, arguments, config, skip_if_cached=True, force_relearn=False
):
    """Learn from maxcount read articles per feed (not total).

    Args:
        rss: RSS backend
        title_queue: Queue to store learned articles
        url_queue: Queue (unused, for compatibility)
        arguments: Command line arguments
        config: Configuration dictionary
        skip_if_cached: Skip learning if cache is already populated (default True)
        force_relearn: Force re-learning regardless of cache (default False)
    """
    # Skip learning if we already have a cached queue (don't re-learn every time)
    # unless force_relearn is True (for periodic retries of failed feeds)
    if not force_relearn and skip_if_cached and len(title_queue) > 0:
        if arguments.debug:
            print_time_message(
                arguments, f"Debug: Using cached {len(title_queue)} learned articles"
            )
        return title_queue, url_queue

    # If force re-learning, clear the queue to rebuild it
    if force_relearn and len(title_queue) > 0:
        if arguments.debug:
            print_time_message(arguments, "Debug: Force re-learning to retry failed feeds...")
        title_queue.clear()

    maxcount_per_feed = int(config.get("newsdedup", {}).get("maxcount", 50))
    feeds = rss.get_feeds()
    total_learned = 0

    if arguments.debug:
        print_time_message(
            arguments,
            f"Debug: Found {len(feeds)} feeds, learning {maxcount_per_feed} articles per feed...",
        )

    for feed in feeds:
        learned_from_feed = 0
        feed_batch = 0

        # Learn up to maxcount_per_feed articles from this feed
        while learned_from_feed < maxcount_per_feed:
            try:
                limit = min(maxcount_per_feed - learned_from_feed, DEFAULT_BATCH_SIZE)
                start_id = feed_batch * DEFAULT_BATCH_SIZE

                articles = rss.get_headlines(
                    feed_id=feed.id, view_mode="all_articles", since_id=start_id, limit=limit
                )

                if not articles:
                    break

                for article in articles:
                    if not article.unread:
                        title_queue.append(
                            LearnedArticle(
                                title=article.title,
                                url=normalize_url(article.link)
                                if hasattr(article, "link") and article.link
                                else "",
                                feed_id=feed.id,
                            )
                        )
                        learned_from_feed += 1
                        total_learned += 1

                feed_batch += 1
            except Exception as e:  # pylint: disable=broad-except
                if arguments.debug:
                    print_time_message(
                        arguments, f"Debug: Skipped '{feed.title}' due to error: {type(e).__name__}"
                    )
                break

        if arguments.debug and learned_from_feed > 0:
            print_time_message(
                arguments, f"Debug: Learned {learned_from_feed} titles from '{feed.title}'"
            )

    if arguments.verbose:
        print_time_message(
            arguments, f"Learned titles from {total_learned} read articles across all feeds."
        )
    return title_queue, url_queue


def compare_to_queue(
    queue,
    head,
    ratio,
    arguments,
    similarity_method="token_sort",
    internal_only_feeds=None,
    feed_id=None,
):
    """Compare current title to all in queue.

    Args:
        queue: List of LearnedArticle objects
        head: Current article to check
        ratio: Similarity threshold
        arguments: Command line arguments
        similarity_method: Method for similarity calculation
        internal_only_feeds: Set of feed IDs that should only compare internally
        feed_id: Current article's feed ID
    """
    if internal_only_feeds is None:
        internal_only_feeds = set()

    for item in queue:
        # If current feed is internal-only, skip articles from other feeds
        if feed_id in internal_only_feeds and item.feed_id != feed_id:
            continue

        similarity = calculate_similarity(item.title, head.title, similarity_method)
        if similarity > ratio:
            if arguments.verbose:
                print_time_message(arguments, "### Old title: " + item.title)
                print_time_message(arguments, "### New: " + head.feed_title + ": " + head.title)
                print_time_message(
                    arguments,
                    f"### Ratio: {similarity} (method: {similarity_method})",
                )
            return similarity
    return 0


def check_url_duplicate(url_queue, head, arguments, internal_only_feeds=None, feed_id=None):
    """Check if URL is already seen (duplicate).

    Args:
        url_queue: List of LearnedArticle objects
        head: Current article to check
        arguments: Command line arguments
        internal_only_feeds: Set of feed IDs that should only compare internally
        feed_id: Current article's feed ID
    """
    if not hasattr(head, "link") or not head.link:
        return False

    if internal_only_feeds is None:
        internal_only_feeds = set()

    normalized_url = normalize_url(head.link)

    for item in url_queue:
        # If current feed is internal-only, skip articles from other feeds
        if feed_id in internal_only_feeds and item.feed_id != feed_id:
            continue

        if normalized_url == item.url:
            if arguments.verbose:
                print_time_message(
                    arguments, f"### URL duplicate found: {head.feed_title}: {head.title}"
                )
                print_time_message(arguments, f"### URL: {normalized_url}")
            return True

    return False


def handle_known_news(rss, head, nostar_list, arguments, dry_run=False):
    """Mark read and add star. Might change in the future."""
    action = "WOULD MARK" if dry_run else "MARKED"

    if str(head.feed_id) in nostar_list:
        if not dry_run:
            rss.mark_read(head.id)
        message = f"[{action} READ] {head.feed_title}: {head.title}"
        if arguments.verbose or dry_run:
            print_time_message(arguments, message)
    else:
        if not dry_run:
            rss.mark_starred(head.id)
            rss.mark_read(head.id)
        message = f"[{action} READ+STARRED] {head.feed_title}: {head.title}"
        if dry_run or arguments.verbose:
            print_time_message(arguments, message)


def print_time_message(arguments, message):
    """Print time and message."""
    try:
        if arguments.daemon:
            print(message, flush=True)
        else:
            print(time.strftime("%Y-%m-%d %H:%M:%S:", time.gmtime()), message, flush=True)
    except Exception as error:  # pylint: disable=broad-except
        if arguments.debug:
            print("Debug: Error in print_time_message: ", str(error), flush=True)


def monitor_rss(rss, title_queue, url_queue, arguments, configuration, saved_state=0):
    """Main function to check new rss posts.

    Args:
        rss: RSS backend
        title_queue: Queue of learned article titles
        url_queue: Queue of learned article URLs (unused, kept for compatibility)
        arguments: Command line arguments
        configuration: Configuration dictionary
        saved_state: Last processed article ID (for resuming)

    Returns:
        Last processed article ID (to be saved as state)
    """
    newsdedup_config = configuration.get("newsdedup", {})

    ignore_list = newsdedup_config.get("ignore", "").split(",")
    nostar_list = newsdedup_config.get("nostar", "").split(",")
    ratio = int(newsdedup_config.get("ratio", 80))
    sleeptime = int(newsdedup_config.get("sleep", 60))

    # Get similarity method from config, default to "combined" for better accuracy
    similarity_method = newsdedup_config.get("similarity_method", "combined")

    # Get URL deduplication setting from config, default to True
    check_urls = newsdedup_config.get("check_urls", True)

    # Get feeds that should only compare internally
    feeds_config = configuration.get("feeds", {})
    internal_only_list = feeds_config.get("internal_only", [])
    internal_only_feeds = set(internal_only_list) if internal_only_list else set()

    headlines = []

    # Use saved state if available, otherwise get latest
    if saved_state > 0:
        start_id = saved_state
    else:
        start_id = (
            rss.get_headlines(view_mode="all_articles", limit=1)[0].id - rss.get_unread_count()
        )

    while True:
        try:
            headlines = rss.get_headlines(since_id=start_id, view_mode="unread")
        except Exception:  # pylint: disable=broad-except
            print_time_message(arguments, "Exception when trying to get feeds.")

        if arguments.dry_run:
            print_time_message(arguments, "=== DRY RUN MODE ===")
            print_time_message(arguments, f"Found {len(headlines)} unread articles to check.")

        duplicate_count = 0
        for head in headlines:
            start_id = max(start_id, head.id)
            if arguments.verbose:
                print_time_message(arguments, head.feed_title + ": " + head.title)
            if (not head.is_updated) and (str(head.feed_id) not in ignore_list):
                is_duplicate = False

                # Check URL-based duplication first
                if check_urls and check_url_duplicate(
                    title_queue, head, arguments, internal_only_feeds, head.feed_id
                ):
                    is_duplicate = True

                # Then check title-based duplication
                if (
                    not is_duplicate
                    and compare_to_queue(
                        title_queue,
                        head,
                        ratio,
                        arguments,
                        similarity_method,
                        internal_only_feeds,
                        head.feed_id,
                    )
                    > 0
                ):
                    is_duplicate = True

                if is_duplicate:
                    duplicate_count += 1
                    handle_known_news(rss, head, nostar_list, arguments, dry_run=arguments.dry_run)

            # Add current article to learned queue for future comparisons
            title_queue.append(
                LearnedArticle(
                    title=head.title,
                    url=normalize_url(head.link) if hasattr(head, "link") and head.link else "",
                    feed_id=head.feed_id,
                )
            )

        if arguments.dry_run:
            print_time_message(arguments, f"Total duplicates found: {duplicate_count}")
            print_time_message(arguments, "=== END DRY RUN ===")
            return start_id

        if arguments.debug:
            print_time_message(arguments, "Sleeping.")
        time.sleep(sleeptime)

    return start_id


def run(rss_api, title_queue, url_queue, args, configuration):
    """Main loop."""
    # Load saved state
    last_id = load_state()
    if args.debug and last_id > 0:
        print_time_message(args, f"Debug: Resuming from article ID {last_id}")

    # Get retry interval from config (default: retry every 10 iterations)
    newsdedup_config = configuration.get("newsdedup", {})
    retry_interval = int(newsdedup_config.get("learning_retry_interval", 10))
    iteration_count = 0

    while True:
        try:
            iteration_count += 1

            # Force re-learn every retry_interval iterations to retry failed feeds
            force_relearn = (iteration_count % retry_interval == 0) and iteration_count > 0

            title_queue, url_queue = learn_last_read(
                rss_api, title_queue, url_queue, args, configuration, force_relearn=force_relearn
            )
            last_id = monitor_rss(
                rss_api, title_queue, url_queue, args, configuration, saved_state=last_id
            )
            # Save state after successful run
            save_state(last_id)

            # In dry-run mode, exit after one iteration
            if args.dry_run:
                break

            # In daemon mode, continue looping (monitor_rss handles sleep)
            # In non-daemon mode, exit after one iteration
            if not args.daemon:
                break
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as error:  # pylint: disable=broad-except
            print_time_message(args, f"Error in monitor_rss: {type(error).__name__}: {error}")
            if args.debug:
                import traceback

                print_time_message(args, "Debug: Full traceback:")
                traceback.print_exc()


def main():
    """Main function to handle arguments and run deduplication."""
    parser = argparse.ArgumentParser(
        prog="newsdedup",
        description="Deduplicate RSS articles in Miniflux.",
        epilog="Report bugs at https://github.com/reuteras/newsdedup/issues",
    )
    parser.add_argument(
        "configFile",
        metavar="newsdedup.toml",
        default="newsdedup.toml",
        nargs="?",
        help="Configuration file (default: newsdedup.toml)",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug output",
    )
    parser.add_argument("-D", "--daemon", action="store_true", help="Run in daemon mode")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress SSL warnings")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be marked as duplicates without making changes",
    )
    args = parser.parse_args()

    if args.quiet:
        logging.captureWarnings(True)
    print("Starting newsdedup...", flush=True)
    configuration = read_configuration(args.configFile)
    print("Configuration loaded", flush=True)
    rss_api = init_backend(configuration)
    print("Miniflux backend initialized", flush=True)
    title_queue = init_title_queue(configuration)
    url_queue = init_url_queue(configuration)
    print("Queues initialized, starting main loop", flush=True)

    run(rss_api, title_queue, url_queue, args, configuration)


if __name__ == "__main__":
    main()
