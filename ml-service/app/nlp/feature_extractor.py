"""
Linguistic/structural feature extraction for a single task description.

Design note: every feature here is something a human labeler could plausibly
reason about when hand-scoring the seed dataset (see data/seed_dataset.csv).
That's deliberate -- it keeps the Random Forest's inputs interpretable enough
to generate an honest explainability blurb per prediction, instead of a black
box score.
"""
import re
from functools import lru_cache

import spacy

_NLP = None

# Keyword banks are lemma-based (spaCy lemmatizes before matching) so
# "reviewed"/"reviewing"/"review" all hit the same bucket.
REPETITION_LEMMAS = {
    "daily", "weekly", "monthly", "every", "each", "repeatedly", "recurring",
    "routine", "constantly", "always", "regularly", "again", "repeat",
    "batch", "bulk",
}
RULE_BASED_LEMMAS = {
    "if", "then", "when", "unless", "whenever", "otherwise", "rule",
    "criterion", "criteria", "threshold", "condition", "trigger",
}
DATA_STRUCTURE_LEMMAS = {
    "spreadsheet", "excel", "csv", "database", "form", "record", "field",
    "row", "column", "table", "api", "file", "document", "invoice",
    "ledger", "report", "dataset", "query",
}
JUDGMENT_LEMMAS = {
    "decide", "decision", "negotiate", "review", "approve", "judge",
    "assess", "evaluate", "persuade", "counsel", "advise", "strategize",
    "brainstorm", "empathize", "mentor", "resolve", "mediate",
}
TOOL_LEMMAS = {
    "excel", "salesforce", "slack", "quickbooks", "zapier", "email",
    "outlook", "gmail", "crm", "erp", "api", "sql", "hubspot", "jira",
    "sheets", "airtable", "selenium", "webhook", "calendar",
}
FREQUENCY_PATTERN = re.compile(
    r"\b(\d+)\s*(times?|x)\s*(per|a|/)\s*(day|week|month|hour)\b", re.IGNORECASE
)


def _get_nlp():
    global _NLP
    if _NLP is None:
        try:
            _NLP = spacy.load("en_core_web_sm")
        except OSError:
            # Falls back to a blank English pipeline with just a tokenizer +
            # lemmatizer rule table if the small model wasn't downloaded --
            # keeps local dev usable without the ~13MB model install blocking
            # first run, at the cost of lemmatization quality.
            _NLP = spacy.blank("en")
    return _NLP


def _lemma_hits(doc, lemma_bank):
    return sum(1 for tok in doc if tok.lemma_.lower() in lemma_bank)


@lru_cache(maxsize=512)
def extract_features(task_text: str) -> dict:
    """Return a dict of named numeric features for one task description.

    Cached because the same task text can be re-scored (e.g. re-analyzing a
    saved workflow) without re-running the spaCy pipeline.
    """
    nlp = _get_nlp()
    doc = nlp(task_text)

    word_count = max(len([t for t in doc if not t.is_punct and not t.is_space]), 1)
    freq_match = FREQUENCY_PATTERN.search(task_text)

    features = {
        "repetitiveness": _lemma_hits(doc, REPETITION_LEMMAS) / word_count,
        "rule_based": _lemma_hits(doc, RULE_BASED_LEMMAS) / word_count,
        "data_structure": _lemma_hits(doc, DATA_STRUCTURE_LEMMAS) / word_count,
        "human_judgment": _lemma_hits(doc, JUDGMENT_LEMMAS) / word_count,
        "tool_mention": _lemma_hits(doc, TOOL_LEMMAS) / word_count,
        "explicit_frequency": 1.0 if freq_match else 0.0,
        "word_count": float(word_count),
    }
    return features


FEATURE_ORDER = [
    "repetitiveness",
    "rule_based",
    "data_structure",
    "human_judgment",
    "tool_mention",
    "explicit_frequency",
    "word_count",
]


def features_to_vector(features: dict) -> list:
    return [features[name] for name in FEATURE_ORDER]
