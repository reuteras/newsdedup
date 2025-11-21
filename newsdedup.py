#!/usr/bin/env python3
"""News deduplication for Miniflux RSS reader."""
#
# Copyright (C) 2015-2025 PR <code@reuteras.se>

import argparse
import configparser
import logging
import re
import sys
import time
from collections import deque

from fuzzywuzzy import fuzz

from backends import create_backend

# Constants
DEFAULT_BATCH_SIZE = 200
HTTP_OK = 200


def read_configuration(config_file):
    """Read configuration file."""
    config = configparser.RawConfigParser()
    config.read(config_file)
    if not config.sections():
        print("Can't find configuration file.")
        sys.exit(1)
    return config


def init_backend(config):
    """Initialize Miniflux RSS backend."""
    try:
        return create_backend(config)
    except Exception as error:  # pylint: disable=broad-except
        print(f"Could not initialize Miniflux backend: {error}")
        sys.exit(1)


def init_title_queue(config):
    """Init deque queue to store handled titles."""
    maxcount = int(config.get("newsdedup", "maxcount"))
    return deque(maxlen=maxcount)


def init_url_queue(config):
    """Init deque queue to store handled URLs."""
    maxcount = int(config.get("newsdedup", "maxcount"))
    return deque(maxlen=maxcount)


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


def learn_last_read(rss, title_queue, url_queue, arguments, config):
    """Get maxcount of read RSS and add to queue."""
    maxlearn = int(config.get("newsdedup", "maxcount"))
    feeds = rss.get_feeds()
    start_id = (
        rss.get_headlines(feed_id=feeds[3].id, view_mode="all_articles", limit=1)[0].id
        - maxlearn
        - rss.get_unread_count()
    )
    learned = 0

    if arguments.debug:
        print_time_message(arguments, "Debug: start_id " + str(start_id) + ".")
    while learned < maxlearn:
        limit = min(maxlearn, DEFAULT_BATCH_SIZE)
        headlines = rss.get_headlines(
            feed_id=feeds[3].id, view_mode="all_articles", since_id=start_id + learned, limit=limit
        )
        for article in headlines:
            if not article.unread:
                title_queue.append(article.title)
                if hasattr(article, "link") and article.link:
                    url_queue.append(normalize_url(article.link))
                learned += 1
        if arguments.debug:
            print_time_message(
                arguments,
                "Debug: Learned titles from " + str(learned) + " RSS articles.",
            )
    if arguments.verbose:
        print_time_message(arguments, "Learned titles from " + str(learned) + " RSS articles.")
    return title_queue, url_queue


def compare_to_queue(queue, head, ratio, arguments, similarity_method="token_sort"):
    """Compare current title to all in queue."""
    for item in queue:
        similarity = calculate_similarity(item, head.title, similarity_method)
        if similarity > ratio:
            if arguments.verbose:
                print_time_message(arguments, "### Old title: " + item)
                print_time_message(arguments, "### New: " + head.feed_title + ": " + head.title)
                print_time_message(
                    arguments,
                    f"### Ratio: {similarity} (method: {similarity_method})",
                )
            return similarity
    return 0


def check_url_duplicate(url_queue, head, arguments):
    """Check if URL is already seen (duplicate)."""
    if not hasattr(head, "link") or not head.link:
        return False

    normalized_url = normalize_url(head.link)

    if normalized_url in url_queue:
        if arguments.verbose:
            print_time_message(
                arguments, f"### URL duplicate found: {head.feed_title}: {head.title}"
            )
            print_time_message(arguments, f"### URL: {normalized_url}")
        return True

    return False


def handle_known_news(rss, head, nostar_list, arguments):
    """Mark read and add stare. Might change in the future."""
    if str(head.feed_id) in nostar_list:
        rss.mark_read(head.id)
        if arguments.verbose:
            print_time_message(arguments, "### nostar: " + head.feed_title + ": " + head.title)
    else:
        rss.mark_starred(head.id)
        rss.mark_read(head.id)


def print_time_message(arguments, message):
    """Print time and message."""
    try:
        if arguments.daemon:
            print(message)
        else:
            print(time.strftime("%Y-%m-%d %H:%M:%S:", time.gmtime()), message)
    except Exception as error:  # pylint: disable=broad-except
        if arguments.debug:
            print("Debug: Error in print_time_message: ", str(error))


def monitor_rss(rss, title_queue, url_queue, arguments, configuration):
    """Main function to check new rss posts."""
    ignore_list = configuration.get("newsdedup", "ignore").split(",")
    nostar_list = configuration.get("newsdedup", "nostar").split(",")
    ratio = int(configuration.get("newsdedup", "ratio"))
    sleeptime = int(configuration.get("newsdedup", "sleep"))

    # Get similarity method from config, default to "combined" for better accuracy
    try:
        similarity_method = configuration.get("newsdedup", "similarity_method")
    except Exception:  # pylint: disable=broad-except
        similarity_method = "combined"

    # Get URL deduplication setting from config, default to True
    try:
        check_urls = configuration.getboolean("newsdedup", "check_urls")
    except Exception:  # pylint: disable=broad-except
        check_urls = True

    headlines = []

    start_id = rss.get_headlines(view_mode="all_articles", limit=1)[0].id - rss.get_unread_count()

    while True:
        try:
            headlines = rss.get_headlines(since_id=start_id, view_mode="unread")
        except Exception:  # pylint: disable=broad-except
            print_time_message(arguments, "Exception when trying to get feeds.")
        for head in headlines:
            start_id = max(start_id, head.id)
            if arguments.verbose:
                print_time_message(arguments, head.feed_title + ": " + head.title)
            if (not head.is_updated) and (str(head.feed_id) not in ignore_list):
                is_duplicate = False

                # Check URL-based duplication first
                if check_urls and check_url_duplicate(url_queue, head, arguments):
                    is_duplicate = True

                # Then check title-based duplication
                if (
                    not is_duplicate
                    and compare_to_queue(title_queue, head, ratio, arguments, similarity_method) > 0
                ):
                    is_duplicate = True

                if is_duplicate:
                    handle_known_news(rss, head, nostar_list, arguments)

            title_queue.append(head.title)
            if hasattr(head, "link") and head.link:
                url_queue.append(normalize_url(head.link))

        if arguments.debug:
            print_time_message(arguments, "Sleeping.")
        time.sleep(sleeptime)


def run(rss_api, title_queue, url_queue, args, configuration):
    """Main loop."""
    while True:
        try:
            monitor_rss(rss_api, title_queue, url_queue, args, configuration)
        except KeyboardInterrupt:
            sys.exit(1)
        except Exception as error:  # pylint: disable=broad-except
            print_time_message(args, "Exception in monitor_rss.")
            if args.debug:
                print_time_message(args, "Debug: Message: " + str(error))


def main():
    """Main function to handle arguments and run deduplication."""
    parser = argparse.ArgumentParser(
        prog="newsdedup",
        description="Deduplicate RSS articles in Miniflux.",
        epilog="Report bugs at https://github.com/reuteras/newsdedup/issues",
    )
    parser.add_argument(
        "configFile",
        metavar="newsdedup.cfg",
        default="newsdedup.cfg",
        nargs="?",
        help="Configuration file (default: newsdedup.cfg)",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug output",
    )
    parser.add_argument("-D", "--daemon", action="store_true", help="Run in daemon mode")
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress SSL warnings"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    if args.quiet:
        logging.captureWarnings(True)
    configuration = read_configuration(args.configFile)
    rss_api = init_backend(configuration)
    title_queue = init_title_queue(configuration)
    url_queue = init_url_queue(configuration)
    learn_last_read(rss_api, title_queue, url_queue, args, configuration)

    run(rss_api, title_queue, url_queue, args, configuration)


if __name__ == "__main__":
    main()
