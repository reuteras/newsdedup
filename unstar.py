#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unstar RSS articles."""
#
# Copyright (C) 2015 PR <code@reuteras.se>

import argparse
import logging
import operator

import newsdedup

def unstar_unread(rss_api, args, configuration):
    """Unstar messages"""
    if isinstance(args.limit, int):
        limit = args.limit
    else:
        limit = args.limit[0]
    if args.shorten:
        import googl
        googleapi = googl.Googl(configuration.get('google', 'shortener'))

    headlines = rss_api.get_headlines(feed_id=-1,
                                      view_mode='all_articles', show_excerpt=False)
    while headlines:
        listed = 0
        read_list = []
        headlines_sorted = sorted(headlines, key=operator.attrgetter('feed_id'))
        for head in headlines_sorted:
            if args.shorten:
                try:
                    link = googleapi.shorten(head.link)['id']
                except: # pylint: disable=bare-except
                    link = head.link
            else:
                link = head.link
            message = str(head.feed_id) +": " + head.feed_title + ": " + head.title + ": " + link
            read_list.append(head.id)
            print(message)
            listed = listed + 1
            if listed == limit or listed == len(headlines_sorted):
                listed = 0
                print("#"*80)
                unstar = input("Unstar messages? (y/n): ")
                if unstar == "y":
                    for read_id in read_list:
                        rss_api.update_article(read_id, 0, 0)
        headlines = rss_api.get_headlines(feed_id=-1,
                                          view_mode='all_articles', show_excerpt=False)

def main():
    """Main function to handle arguments."""
    parser = argparse.ArgumentParser(
        prog='unstar',
        description='''Unstar tool for newsdedup.''',
        epilog='''Program made by PR, @reuteras on Twitter.
            If you find a bug please let me know.''')
    parser.add_argument('configFile', metavar='newsdedup.cfg',
                        default='newsdedup.cfg', nargs='?',
                        help='Specify configuration file.')
    parser.add_argument('-q', '--quiet', action="store_true",
                        help='Quiet, i.e. catch SSL warnings.')
    parser.add_argument('-s', '--shorten', action="store_true",
                        help='Shorten urls using Google.')
    parser.add_argument('-v', '--verbose', action="store_true",
                        help='Verbose output.')
    parser.add_argument('-l', '--limit', default=20, nargs=1, type=int,
                        help='Limit output to x (20 default).')
    args = parser.parse_args()

    if args.quiet:
        logging.captureWarnings(True)
    configuration = newsdedup.read_configuration(args.configFile)
    rss_api = newsdedup.init_ttrss(configuration)
    unstar_unread(rss_api, args, configuration)

if __name__ == '__main__':
    main()
