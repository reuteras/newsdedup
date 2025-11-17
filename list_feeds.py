#!/usr/bin/env python
"""List feeds."""
#
# Copyright (C) 2021 PR <code@reuteras.se>

from newsdedup import init_backend, read_configuration


def main():
    """Main function."""
    configuration = read_configuration("newsdedup.cfg")
    rss_api = init_backend(configuration)

    try:
        for category in rss_api.get_categories():
            # For TTRSS, use cat_id parameter
            if hasattr(rss_api, "client"):
                for feed in rss_api.get_feeds(cat_id=category.id):
                    print(feed.id, feed.title)
            # For Miniflux, filter feeds by category manually
            else:
                for feed in rss_api.get_feeds():
                    if feed.category_id == category.id:
                        print(feed.id, feed.title)
    except Exception as error:  # pylint: disable=broad-except
        print(f"Error listing feeds: {error}")
        # Fallback: just list all feeds without category filtering
        for feed in rss_api.get_feeds():
            print(feed.id, feed.title)


if __name__ == "__main__":
    main()
