import os
import subprocess
import sys

import pytest

from app.nlp.feature_extractor import extract_features
from app.scoring.classifier import ModelNotTrainedError, score_task

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "model.pkl")


@pytest.fixture(scope="module", autouse=True)
def ensure_model_trained():
    if not os.path.exists(MODEL_PATH):
        subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "..", "models", "train_model.py")],
            check=True,
        )


def test_highly_automatable_task_scores_above_threshold():
    features = extract_features(
        "Back up the database every night at midnight on a fixed schedule."
    )
    result = score_task(features)
    assert result["score"] >= 70
    assert "explanation" in result


def test_judgment_heavy_task_scores_low():
    features = extract_features(
        "Negotiate a multi-year lease renewal for the office space."
    )
    result = score_task(features)
    assert result["score"] < 40


def test_score_is_bounded_0_to_100():
    features = extract_features("Do a task.")
    result = score_task(features)
    assert 0 <= result["score"] <= 100
