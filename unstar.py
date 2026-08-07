#!/usr/bin/env python3
"""Unstar RSS articles."""
#
# Copyright (C) 2015-2023 PR <code@reuteras.se>

import argparse
import logging
import operator
import re
import sys

import newsdedup


def shorten_url(args, head):
    """Shorten a url."""
    link = head.link

    if args.notrack:
        link = re.sub(r"\?(utm|at_me).*$", "", link)

    return link


def unstar_unread(rss_api, args):
    """Unstar messages"""
    limit = args.limit if isinstance(args.limit, int) else args.limit[0]

    headlines = rss_api.get_headlines(view_mode="starred", show_excerpt=False)
    while headlines:
        listed = 0
        read_list = []
        headlines_sorted = sorted(headlines, key=operator.attrgetter("feed_id"))
        for head in headlines_sorted:
            link = shorten_url(args, head)

            feed_title = head.feed_title
            message = str(head.feed_id) + ": " + feed_title + ": " + head.title + ": " + link
            read_list.append(head.id)
            print(message)
            listed = listed + 1
            if (limit > 0 and listed % limit == 0) or listed == len(headlines_sorted):
                print("#" * 80)
                unstar = input("Unstar messages? (y/n/q): ")
                if unstar == "y":
                    for read_id in read_list:
                        rss_api.toggle_starred(read_id)
                read_list = []
                if unstar == "q":
                    sys.exit()
        headlines = rss_api.get_headlines(view_mode="starred", show_excerpt=False)


def main():
    """Main function to handle arguments."""
    parser = argparse.ArgumentParser(
        prog="unstar",
        description="""Unstar tool for newsdedup.""",
        epilog="""Program made by PR, @reuteras@infosec.exchange on Mastodon.
            If you find a bug please let me know.""",
    )
    parser.add_argument(
        "configFile",
        metavar="newsdedup.toml",
        default="newsdedup.toml",
        nargs="?",
        help="Specify configuration file.",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Quiet, i.e. catch SSL warnings."
    )
    parser.add_argument(
        "-n",
        "--notrack",
        action="store_true",
        help="Remove some known trackers from the URL.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output.")
    parser.add_argument(
        "-l",
        "--limit",
        default=20,
        nargs=1,
        type=int,
        help="Limit output to x (20 default).",
    )
    args = parser.parse_args()

    if args.quiet:
        logging.captureWarnings(True)
    configuration = newsdedup.read_configuration(args.configFile)
    rss_api = newsdedup.init_backend(configuration)
    unstar_unread(rss_api, args)


# Run main function
if __name__ == "__main__":
    main()
