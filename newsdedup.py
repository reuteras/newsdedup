#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""News dedup for Tiny Tiny RSS."""
#
# Copyright (C) 2015 PR <code@reuteras.se>

import argparse
import configparser
import logging
import sys
import time
from collections import deque

from fuzzywuzzy import fuzz
from ttrss.client import TTRClient
from ttrss.exceptions import TTRApiDisabled, TTRAuthFailure, TTRNotLoggedIn


def read_configuration(config_file):
    """Read configuration file."""
    config = configparser.RawConfigParser()
    config.read(config_file)
    if not config.sections():
        print("Can't find configuration file.")
        sys.exit(1)
    return config


def init_ttrss(config):
    """Init Tiny tiny RSS API."""
    try:
        hostname = config.get("ttrss", "hostname")
        username = config.get("ttrss", "username")
        password = config.get("ttrss", "password")
    except Exception:  # pylint: disable=broad-except
        print("Could not read needed config parameters.")
        sys.exit(1)
    try:
        client = TTRClient(hostname, username, password, auto_login=False)
        client.login()
    except (TTRApiDisabled, TTRNotLoggedIn, TTRAuthFailure) as error:
        print("Couldn't setup TTRClient: ", error)
        sys.exit(1)
    return client


def init_title_queue(config):
    """Init deque queue to store handled titles."""
    maxcount = int(config.get("newsdedup", "maxcount"))
    return deque(maxlen=maxcount)


def learn_last_read(rss, queue, arguments, config):
    """Get maxcount of read RSS and add to queue."""
    maxlearn = int(config.get("newsdedup", "maxcount"))
    feeds = rss.get_feeds()
    start_id = (
        feeds[3].headlines(view_mode="all_articles", limit=1)[0].id
        - maxlearn
        - rss.get_unread_count()
    )
    learned = 0

    if arguments.debug:
        print_time_message(arguments, "Debug: start_id " + str(start_id) + ".")
    while learned < maxlearn:
        limit = 200 if maxlearn > 200 else maxlearn
        headlines = feeds[3].headlines(
            view_mode="all_articles", since_id=start_id + learned, limit=limit
        )
        for article in headlines:
            if not article.unread:
                queue.append(article.title)
                learned += 1
        if arguments.debug:
            print_time_message(
                arguments,
                "Debug: Learned titles from " + str(learned) + " RSS articles.",
            )
    if arguments.verbose:
        print_time_message(
            arguments, "Learned titles from " + str(learned) + " RSS articles."
        )
    return queue


def compare_to_queue(queue, head, ratio, arguments):
    """Compare current title to all in queue."""
    for item in queue:
        if fuzz.token_sort_ratio(item, head.title) > ratio:
            if arguments.verbose:
                print_time_message(arguments, "### Old title: " + item)
                print_time_message(
                    arguments, "### New: " + head.feed_title + ": " + head.title
                )
                print_time_message(
                    arguments,
                    "### Ratio:" + str(fuzz.token_sort_ratio(item, head.title)),
                )
            return fuzz.token_sort_ratio(item, head.title)
    return 0


def handle_known_news(rss, head, nostar_list, arguments):
    """Mark read and add stare. Might change in the future."""
    if str(head.feed_id) in nostar_list:
        rss.mark_read(head.id)
        if arguments.verbose:
            print_time_message(
                arguments, "### nostar: " + head.feed_title + ": " + head.title
            )
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


def monitor_rss(rss, queue, arguments, configuration):
    """Main function to check new rss posts."""
    ignore_list = configuration.get("newsdedup", "ignore").split(",")
    nostar_list = configuration.get("newsdedup", "nostar").split(",")
    ratio = int(configuration.get("newsdedup", "ratio"))
    sleeptime = int(configuration.get("newsdedup", "sleep"))
    headlines = []

    start_id = (
        rss.get_headlines(view_mode="all_articles", limit=1)[0].id
        - rss.get_unread_count()
    )

    while True:
        try:
            headlines = rss.get_headlines(since_id=start_id, view_mode="unread")
        except Exception:  # pylint: disable=broad-except
            print_time_message(arguments, "Exception when trying to get feeds.")
        for head in headlines:
            if head.id > start_id:
                start_id = head.id
            if arguments.verbose:
                print_time_message(arguments, head.feed_title + ": " + head.title)
            if (not head.is_updated) and (str(head.feed_id) not in ignore_list):
                if compare_to_queue(queue, head, ratio, arguments) > 0:
                    handle_known_news(rss, head, nostar_list, arguments)
            queue.append(head.title)
        if arguments.debug:
            print_time_message(arguments, "Sleeping.")
        time.sleep(sleeptime)


def run(rss_api, title_queue, args, configuration):
    """Main loop."""
    while True:
        try:
            monitor_rss(rss_api, title_queue, args, configuration)
        except KeyboardInterrupt:
            sys.exit(1)
        except Exception as error:  # pylint: disable=broad-except
            print_time_message(args, "Exception in monitor_rss.")
            if args.debug:
                print_time_message(args, "Debug: Message: " + str(error))


def main():
    """Main function to handle arguments."""
    parser = argparse.ArgumentParser(
        prog="newsdedup",
        description="""This programs dedups RSS articles handled by
            Tiny tiny RSS.""",
        epilog="""Program made by PR, @reuteras on Twitter.
            If you find a bug please let me know.""",
    )
    parser.add_argument(
        "configFile",
        metavar="newsdedup.cfg",
        default="newsdedup.cfg",
        nargs="?",
        help="Specify configuration file.",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Debug output (separate from verbose).",
    )
    parser.add_argument("-D", "--daemon", action="store_true", help="Run as daemon.")
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Quiet, i.e. catch SSL warnings."
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output.")
    args = parser.parse_args()

    if args.quiet:
        logging.captureWarnings(True)
    configuration = read_configuration(args.configFile)
    rss_api = init_ttrss(configuration)
    title_queue = init_title_queue(configuration)
    learn_last_read(rss_api, title_queue, args, configuration)

    run(rss_api, title_queue, args, configuration)


if __name__ == "__main__":
    main()
