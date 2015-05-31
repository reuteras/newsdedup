#!/usr/bin/env python                                                                                                   
# -*- coding: utf-8 -*- 
#
# Copyright (C) 2015 Peter Reuterås

import ConfigParser
import argparse
import sys
import time
from collections import deque
from fuzzywuzzy import fuzz
from time import gmtime, strftime
from ttrss.client import TTRClient

# Read the configuration file                                                                                           
# configFile: File with with configuration information. Default newsdedup.cfg
def read_configuration(configFile):
    configuration = ConfigParser.RawConfigParser()
    configuration.read(configFile)
    if configuration.sections() == []:
        print "Can't find configuration file."
        sys.exit(1)
    return configuration

def init_ttrss(configuration):
    hostname = configuration.get('ttrss', 'hostname')
    username = configuration.get('ttrss', 'username')
    password = configuration.get('ttrss', 'password')
    return TTRClient(hostname, username, password, auto_login=True)

def init_queue(configuration):
    maxcount = int(configuration.get('newsdedup', 'maxcount'))
    return deque(maxlen = maxcount)

def init_ignore_list(configuration):
    ignorestring = configuration.get('newsdedup', 'ignore')
    return ignorestring.split(',')

def compare_to_queue(queue, title, ratio, verbose):
    for item in queue:
        if fuzz.token_sort_ratio(item, title) > ratio:
            if verbose:
                print "Old: ", item
                print "New: ", title
                print "Ratio: ", fuzz.token_sort_ratio(item, title)
            return fuzz.token_sort_ratio(item, title)
    return 0

def handle_known_news(rss, head, ignore_list):
    if not head.feed_id in ignore_list:
        if not head.is_updated:
            rss.update_article(head.id, 1, 0)
            rss.mark_read(head.id)

def learn_last_read(rss, queue, args, configuration):
    maxlearn = int(configuration.get('newsdedup', 'maxcount'))
    if rss.get_unread_count() > 0:
        feeds = rss.get_feeds(unread_only = True)
        headlines = feeds[1].headlines(view_mode='unread')
        try:
            min_id = headlines[0].id
        except:
            return queue
        for article in headlines:
            if article.id < min_id:
                min_id = article.id
        min_id -= maxlearn + 1
    else:
        feeds = rss.get_feeds()
        headlines = feeds[1].headlines(view_mode = 'all_articles', limit=maxlearn)
        try:
            max_id = headlines[0].id
        except:
            return queue
        for article in headlines:
            if article.id > max_id:
                max_id = article.id
        min_id = max_id - maxlearn
    learned = 0
    start_id = min_id
    while learned < maxlearn:
        headlines = feeds[1].headlines(view_mode = 'all_articles', since_id = min_id + learned, limit = maxlearn)
        for article in headlines:
            if not article.unread:
                queue.append(article.title)
                learned += 1
    if args.verbose:
        print "Learned titles from", learned, "RSS articles."
    return queue                

def monitor_rss(rss, queue, ignore_list, args, configuration):
    max_id = 0
    ratio = int(configuration.get('newsdedup', 'ratio'))
    sleeptime = int(configuration.get('newsdedup', 'sleep'))
    headlines = []
    while True:
        feeds = rss.get_feeds(unread_only = True)
        if max_id == 0:
            try:
                headlines = feeds[1].headlines(view_mode='unread')
            except:
                pass
        else:
            try:
                headlines = feeds[1].headlines(since_id = max_id, view_mode='unread')
            except:
                pass
        for head in headlines:
            if head.id > max_id:
                max_id = head.id + 1
            if args.verbose:
                current_time=strftime("%Y-%m-%d %H:%M:%S:", gmtime())
                print current_time, head.title
            if compare_to_queue(queue, head.title, ratio, args.verbose) > 0:
                handle_known_news(rss, head, ignore_list)
            queue.append(head.title)
        if args.debug:
            current_time=strftime("%Y-%m-%d %H:%M:%S:", gmtime())
            print current_time, "Sleeping."
        time.sleep(sleeptime)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='newsdedup',
        description='''This programs is my first try in trying to "dedup" my RSS feeds. 
            
            Default configuration file is newsdedup.cfg in the current directory.''',
         epilog='''Program made by Peter Reuterås, @reuteras. If you find a 
            bug please let me know.''')
    parser.add_argument('configFile', metavar='newsdedup.cfg', default='newsdedup.cfg', nargs='?', help='Specify configuration file.')
    parser.add_argument('-v', '--verbose', action="store_true", help='Verbose output.')
    parser.add_argument('-d', '--debug', action="store_true", help='Debug output (separate from verbose).')
    args = parser.parse_args()

    configuration = read_configuration(args.configFile)
    rss = init_ttrss(configuration)
    queue = init_queue(configuration)
    ignore_list = init_ignore_list(configuration)
    learn_last_read(rss, queue, args, configuration)
    monitor_rss(rss, queue, ignore_list, args, configuration)
