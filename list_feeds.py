#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""List feeds."""
#
# Copyright (C) 2021 PR <code@reuteras.se>

from newsdedup import read_configuration, init_ttrss


def main():
    """Main function."""
    configuration = read_configuration("newsdedup.cfg")
    rss_api = init_ttrss(configuration)

    for category in rss_api.get_categories():
        for feed in rss_api.get_feeds(cat_id=category.id):
            print(feed.id, feed.title)

if __name__ == '__main__':
    main()
