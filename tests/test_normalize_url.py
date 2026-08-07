from newsdedup import normalize_url


def test_upgrades_http_to_https():
    assert normalize_url("http://example.com/a") == "https://example.com/a"


def test_strips_fragment():
    assert normalize_url("https://example.com/a#section") == "https://example.com/a"


def test_strips_lone_tracking_param():
    assert normalize_url("https://example.com/a?utm_source=foo") == "https://example.com/a"


def test_strips_trailing_tracking_param_keeps_others():
    url = "https://example.com/a?id=1&utm_source=foo&utm_medium=bar"
    assert normalize_url(url) == "https://example.com/a?id=1"


def test_strips_various_tracking_params():
    for param in (
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
        "msclkid",
        "mc_cid",
        "mc_eid",
    ):
        url = f"https://example.com/a?{param}=xyz"
        assert normalize_url(url) == "https://example.com/a"


def test_leaves_non_tracking_query_untouched():
    url = "https://example.com/a?id=42"
    assert normalize_url(url) == "https://example.com/a?id=42"
