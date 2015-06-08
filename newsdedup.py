#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""News dedup for Tiny Tiny RSS."""
#
# Copyright (C) 2015 Peter Reuterås

import ConfigParser
import argparse
import daemon
import logging
import sys
import time
from collections import deque
from fuzzywuzzy import fuzz
from time import gmtime, strftime
from ttrss.client import TTRClient

context = daemon.DaemonContext(
    umask=0o002,
)

context.signal_map = {
}

def read_configuration(config_file):
    """Read configuration file."""
    config = ConfigParser.RawConfigParser()
    config.read(config_file)
    if config.sections() == []:
        print "Can't find configuration file."
        sys.exit(1)
    return config

def init_ttrss(config):
    """Init Tiny tiny RSS API."""
    hostname = config.get('ttrss', 'hostname')
    username = config.get('ttrss', 'username')
    password = config.get('ttrss', 'password')
    return TTRClient(hostname, username, password, auto_login=True)

def init_title_queue(config):
    """Init deque queue to store handled titles."""
    maxcount = int(config.get('newsdedup', 'maxcount'))
    return deque(maxlen=maxcount)

def init_ignore_list(config):
    """Read ignore list from config and store in array."""
    ignorestring = config.get('newsdedup', 'ignore')
    return ignorestring.split(',')

def compare_to_queue(queue, head, ratio, arguments):
    """Compare current title to all in queue."""
    for item in queue:
        if fuzz.token_sort_ratio(item, head.title) > ratio:
            if arguments.verbose:
                print_time_message("### Old title: " + item)
                print_time_message("### New: " + head.feed_title + ": " + head.title)
                print_time_message("### Ratio:" + fuzz.token_sort_ratio(item, head.title))
            return fuzz.token_sort_ratio(item, head.title)
    return 0

def handle_known_news(rss, head):
    """Mark read and add stare. Might change in the future."""
    rss.update_article(head.id, 1, 0)
    rss.mark_read(head.id)

def learn_last_read(rss, queue, arguments, config):
    """Get maxcount of read RSS and add to queue."""
    maxlearn = int(config.get('newsdedup', 'maxcount'))
    feeds = rss.get_feeds()
    headlines = feeds[3].headlines(view_mode='all_articles', limit=1)
    start_id = headlines[0].id - maxlearn - rss.get_unread_count()
    learned = 0
    while learned < maxlearn:
        limit = 200 if maxlearn > 200 else maxlearn
        headlines = feeds[3].headlines(
            view_mode='all_articles',
            since_id=start_id + learned, limit=limit)
        for article in headlines:
            if not article.unread:
                queue.append(article.title)
                learned += 1
    if arguments.verbose:
        print_time_message("Learned titles from " + str(learned) + " RSS articles.")
    return queue

def print_time_message(message):
    """Print time and message."""
    print strftime("%Y-%m-%d %H:%M:%S:", gmtime()), message

def monitor_rss(rss, queue, ignore_list, arguments, config):
    """Main function to check new rss posts."""
    feeds = rss.get_feeds()
    headlines = feeds[3].headlines(view_mode='all_articles', limit=1)
    start_id = headlines[0].id - rss.get_unread_count()
    ratio = int(config.get('newsdedup', 'ratio'))
    sleeptime = int(config.get('newsdedup', 'sleep'))
    headlines = []
    while True:
        feeds = rss.get_feeds(unread_only=True)
        try:
            headlines = feeds[1].headlines(since_id=start_id, view_mode='unread')
        except: # pylint: disable=bare-except
            pass
        for head in headlines:
            if head.id > start_id:
                start_id = head.id
            if arguments.verbose:
                print_time_message(head.feed_title + ": " + head.title)
            if (not head.is_updated) and (not head.feed_id in ignore_list):
                if compare_to_queue(queue, head, ratio, arguments) > 0:
                    handle_known_news(rss, head)
                queue.append(head.title)
        if arguments.debug:
            print_time_message("Sleeping.")
        time.sleep(sleeptime)

def run(rss_api, title_queue, feed_ignore_list, args, configuration):
    """Main loop."""
    while True:
        try:
            monitor_rss(rss_api, title_queue, feed_ignore_list, args, configuration)
        except KeyboardInterrupt:
            sys.exit(1)
        except: # pylint: disable=bare-except
            pass


def main():
    """Main function to handle arguments."""
    parser = argparse.ArgumentParser(
        prog='newsdedup',
        description='''This programs dedups RSS articles handled by
            Tiny tiny RSS.''',
        epilog='''Program made by Peter Reuterås, @reuteras on Twitter.
            If you find a bug please let me know.''')
    parser.add_argument('configFile', metavar='newsdedup.cfg',
            	           default='newsdedup.cfg', nargs='?',
            	           help='Specify configuration file.')
    parser.add_argument('-d', '--debug', action="store_true",
                        help='Debug output (separate from verbose).')
    parser.add_argument('-D', '--daemon', action="store_true",
                        help='Run as daemon.')
    parser.add_argument('-q', '--quiet', action="store_true",
                        help='Quiet, i.e. catch SSL warnings.')
    parser.add_argument('-v', '--verbose', action="store_true",
                        help='Verbose output.')
    args = parser.parse_args()

    if args.quiet:
        logging.captureWarnings(True)
    configuration = read_configuration(args.configFile)
    rss_api = init_ttrss(configuration)
    title_queue = init_title_queue(configuration)
    feed_ignore_list = init_ignore_list(configuration)
    learn_last_read(rss_api, title_queue, args, configuration)

    if args.daemon:
        with context:
            run(rss_api, title_queue, feed_ignore_list, args, configuration)
    else:
        run(rss_api, title_queue, feed_ignore_list, args, configuration)

if __name__ == '__main__':
    main()
