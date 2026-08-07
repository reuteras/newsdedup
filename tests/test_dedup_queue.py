from newsdedup import LearnedArticle, check_url_duplicate, compare_to_queue


def test_compare_to_queue_detects_cross_feed_duplicate(make_article, make_args):
    queue = [LearnedArticle(title="Apple releases new iPhone", url="", feed_id=1)]
    head = make_article(title="Apple releases new iPhone today", feed_title="Feed2", feed_id=2)

    result = compare_to_queue(queue, head, ratio=80, arguments=make_args(), feed_id=2)

    assert result > 80


def test_compare_to_queue_returns_zero_for_unrelated_titles(make_article, make_args):
    queue = [LearnedArticle(title="Completely different story", url="", feed_id=1)]
    head = make_article(title="Apple releases new iPhone today", feed_title="Feed2", feed_id=2)

    result = compare_to_queue(queue, head, ratio=80, arguments=make_args(), feed_id=2)

    assert result == 0


def test_compare_to_queue_internal_only_ignores_other_feeds(make_article, make_args):
    queue = [LearnedArticle(title="Apple releases new iPhone", url="", feed_id=1)]
    head = make_article(title="Apple releases new iPhone today", feed_title="Feed2", feed_id=2)

    result = compare_to_queue(
        queue, head, ratio=80, arguments=make_args(), internal_only_feeds={2}, feed_id=2
    )

    assert result == 0


def test_compare_to_queue_self_dedup_matches_within_same_feed(make_article, make_args):
    feed_seen_articles = {1: {("", "Apple releases new iPhone")}}
    head = make_article(title="Apple releases new iPhone again", feed_title="Feed1", feed_id=1)

    result = compare_to_queue(
        [],
        head,
        ratio=80,
        arguments=make_args(),
        feed_id=1,
        self_dedup_feeds={1},
        feed_seen_articles=feed_seen_articles,
    )

    assert result > 80


def test_check_url_duplicate_false_when_head_has_no_link(make_article, make_args):
    head = make_article(title="x", link="", feed_id=1)

    assert check_url_duplicate([], head, make_args()) is False


def test_check_url_duplicate_true_for_matching_normalized_url(make_article, make_args):
    queue = [LearnedArticle(title="t", url="https://example.com/a", feed_id=1)]
    head = make_article(title="different", link="https://example.com/a?utm_source=x", feed_id=2)

    assert check_url_duplicate(queue, head, make_args()) is True


def test_check_url_duplicate_internal_only_ignores_other_feeds(make_article, make_args):
    queue = [LearnedArticle(title="t", url="https://example.com/a", feed_id=1)]
    head = make_article(title="different", link="https://example.com/a", feed_id=2)

    result = check_url_duplicate(queue, head, make_args(), internal_only_feeds={2}, feed_id=2)

    assert result is False


def test_check_url_duplicate_self_dedup_matches_within_same_feed(make_article, make_args):
    feed_seen_articles = {1: {("https://example.com/a", "t")}}
    head = make_article(title="t2", link="https://example.com/a", feed_id=1)

    result = check_url_duplicate(
        [],
        head,
        make_args(),
        feed_id=1,
        self_dedup_feeds={1},
        feed_seen_articles=feed_seen_articles,
    )

    assert result is True
