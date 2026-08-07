from newsdedup import calculate_similarity, jaccard_similarity


def test_jaccard_identical_strings():
    assert jaccard_similarity("a b c", "a b c") == 100


def test_jaccard_partial_overlap():
    assert jaccard_similarity("a b c", "a b d") == 50


def test_jaccard_no_overlap():
    assert jaccard_similarity("a b c", "d e f") == 0


def test_jaccard_empty_string_returns_zero():
    assert jaccard_similarity("", "a b") == 0
    assert jaccard_similarity("a b", "") == 0


def test_calculate_similarity_identical_titles_is_high_for_every_method():
    title = "Apple releases new iPhone today"
    for method in ("token_sort", "token_set", "partial", "jaccard", "combined"):
        assert calculate_similarity(title, title, method) >= 99


def test_calculate_similarity_detects_reordered_titles():
    a = "Apple releases new iPhone"
    b = "new iPhone released by Apple"
    assert calculate_similarity(a, b, "token_sort") > 80


def test_calculate_similarity_unrelated_titles_is_low():
    a = "Apple releases new iPhone"
    b = "Local weather expected to be sunny tomorrow"
    assert calculate_similarity(a, b, "token_sort") < 50


def test_calculate_similarity_combined_is_at_least_each_component():
    a = "Apple releases new iPhone"
    b = "new iPhone released by Apple"
    combined = calculate_similarity(a, b, "combined")
    assert combined >= calculate_similarity(a, b, "token_sort")
    assert combined >= calculate_similarity(a, b, "token_set")
    assert combined >= jaccard_similarity(a, b)


def test_calculate_similarity_unknown_method_falls_back_to_token_sort():
    a = "Apple releases new iPhone"
    b = "new iPhone released by Apple"
    assert calculate_similarity(a, b, "bogus-method") == calculate_similarity(a, b, "token_sort")
