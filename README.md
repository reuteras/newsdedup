# newsdedup

![Linter](https://github.com/reuteras/newsdedup/workflows/Linter/badge.svg)

A project to de duplicate my news feed.

For a long time I've added a lot of RSS feeds and now I've ended up with a lot
of duplicate entries for big stories. With this project I aim to move duplicates
to starred and mark them as read. This might change in the future if I find a
better way to do it.

To run the code as a daemon under systemd you can do the following steps:

    mkdir -p ~/.config/systemd/user/
    cp newsdedup.service.default ~/.config/systemd/user/newsdedup.service
    systemctl --user enable newsdedup.service
    systemctl --user start newsdedup.service

To watch the logs you can run:

    journalctl -f --user-unit newsdedup

Unmark stared articles from the command line with:

    ./unstar.py -b

## Links

Some of the relevant API:s used in this project.

* [ttrss-python](http://ttrss-python.readthedocs.org/en/latest/)
* [Tiny Tiny RSS - API Reference](https://tt-rss.org/wiki/ApiReference)
* [fuzzywuzzy](https://github.com/seatgeek/fuzzywuzzy)
