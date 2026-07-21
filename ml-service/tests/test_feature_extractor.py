from app.nlp.feature_extractor import extract_features


def test_repetitive_rule_based_task_scores_high_on_automation_features():
    # "every" hits the repetitiveness lemma bank; "threshold" hits the
    # rule-based lemma bank -- the original version of this test used a
    # sentence ("every time... 7 days overdue") that doesn't actually contain
    # any word from RULE_BASED_LEMMAS in feature_extractor.py, so it was
    # asserting something the extractor was never designed to detect.
    features = extract_features(
        "Every time an invoice crosses the 7-day threshold, send a reminder email."
    )
    assert features["repetitiveness"] > 0
    assert features["rule_based"] > 0


def test_judgment_heavy_task_flags_human_judgment():
    features = extract_features(
        "Negotiate final pricing terms with a key enterprise client over a call."
    )
    assert features["human_judgment"] > 0


def test_explicit_frequency_is_detected():
    features = extract_features("Update the shared spreadsheet with sales figures 3 times a day.")
    assert features["explicit_frequency"] == 1.0


def test_no_explicit_frequency_when_absent():
    features = extract_features("Design the branding direction for a new product line.")
    assert features["explicit_frequency"] == 0.0


def test_feature_vector_has_expected_keys():
    features = extract_features("Back up the database every night at midnight.")
    expected_keys = {
        "repetitiveness",
        "rule_based",
        "data_structure",
        "human_judgment",
        "tool_mention",
        "explicit_frequency",
        "word_count",
    }
    assert set(features.keys()) == expected_keys
