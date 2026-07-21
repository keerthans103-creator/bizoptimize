"""
Loads the trained Random Forest and turns raw feature dicts into a
0-100 automatability score plus a human-readable explainability blurb.

The blurb is built from the model's global feature_importances_ combined
with this specific task's feature values -- so it says *which* signals
actually pushed this task's score up or down, not just a canned sentence.
"""
import json
import os

import joblib

from app.nlp.feature_extractor import FEATURE_ORDER, features_to_vector

_MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models")
_MODEL_PATH = os.path.join(_MODEL_DIR, "model.pkl")
_METADATA_PATH = os.path.join(_MODEL_DIR, "model_metadata.json")

_FEATURE_LABELS = {
    "repetitiveness": "repetitive/recurring language",
    "rule_based": "rule-based or conditional logic",
    "data_structure": "structured data or system mentions",
    "human_judgment": "human-judgment language",
    "tool_mention": "specific tool/software integration",
    "explicit_frequency": "an explicitly stated frequency",
    "word_count": "task description length",
}

_model = None
_metadata = None


class ModelNotTrainedError(RuntimeError):
    pass


def _load():
    global _model, _metadata
    if _model is None:
        if not os.path.exists(_MODEL_PATH):
            raise ModelNotTrainedError(
                "models/model.pkl not found. Run `python models/train_model.py` first."
            )
        _model = joblib.load(_MODEL_PATH)
        with open(_METADATA_PATH) as f:
            _metadata = json.load(f)
    return _model, _metadata


def _explain(features: dict, importances: dict) -> str:
    # Rank features by importance * how present they are in this task,
    # then describe the top drivers in plain English.
    scored = []
    for name in FEATURE_ORDER:
        if name == "word_count":
            continue
        value = features[name]
        weight = importances.get(name, 0.0)
        if value > 0:
            scored.append((weight * value, name))

    scored.sort(reverse=True)
    top = [name for _, name in scored[:3]]

    judgment_present = features.get("human_judgment", 0) > 0
    if not top:
        return "Score driven mainly by the task's overall phrasing; no strong repetition, rule, or judgment signals detected."

    drivers = ", ".join(_FEATURE_LABELS[name] for name in top)
    if judgment_present and "human_judgment" not in top:
        return f"High: driven by {drivers} (some human-judgment language present but outweighed by automation signals)."
    return f"Driven by {drivers}."


def score_task(features: dict) -> dict:
    """Returns {"score": int 0-100, "explanation": str, "features": dict}."""
    model, metadata = _load()
    vector = [features_to_vector(features)]
    raw_score = model.predict(vector)[0]
    score = max(0, min(100, round(float(raw_score))))

    return {
        "score": score,
        "explanation": _explain(features, metadata["feature_importances"]),
        "features": features,
        "model_metadata": {
            "holdout_r2": metadata["holdout_r2"],
            "trained_at": metadata["trained_at"],
        },
    }
