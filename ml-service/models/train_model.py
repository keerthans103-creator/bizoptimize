"""
Trains the Random Forest that scores task automatability.

Honesty note (see README methodology section): this is trained on a
hand-labeled *seed* dataset of ~70 example tasks (data/seed_dataset.csv), not
real-world usage data. Labels were assigned by us using a simple rubric
(high repetitiveness + rule-based logic + tool integration -> high score;
negotiation/judgment/strategy -> low score). Treat the reported R^2 as a
sanity check on a tiny held-out split, not a claim of production-grade
accuracy. Retraining on real user data (once collected via the app itself)
is the obvious next step and is called out in the README as future work.

Run with: python models/train_model.py
"""
import json
import os
import sys
from datetime import datetime, timezone

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.nlp.feature_extractor import FEATURE_ORDER, extract_features  # noqa: E402

SEED_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "seed_dataset.csv")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")
METADATA_PATH = os.path.join(os.path.dirname(__file__), "model_metadata.json")


def build_feature_matrix(df: pd.DataFrame):
    rows = [extract_features(text) for text in df["task_text"]]
    X = pd.DataFrame(rows)[FEATURE_ORDER]
    y = df["label_score"].astype(float)
    return X, y


def main():
    df = pd.read_csv(SEED_DATA_PATH)
    X, y = build_feature_matrix(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=6,
        min_samples_leaf=2,
        random_state=42,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": len(df),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "feature_order": FEATURE_ORDER,
        "holdout_r2": round(r2_score(y_test, preds), 3),
        "holdout_mae": round(mean_absolute_error(y_test, preds), 2),
        "feature_importances": dict(
            zip(FEATURE_ORDER, [round(v, 4) for v in model.feature_importances_])
        ),
        "dataset_source": "hand-labeled seed dataset, not real-world usage data",
    }

    joblib.dump(model, MODEL_PATH)
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Model trained on {len(df)} seed examples.")
    print(f"Holdout R^2: {metadata['holdout_r2']}  MAE: {metadata['holdout_mae']}")
    print(f"Saved model to {MODEL_PATH}")
    print(f"Saved metadata to {METADATA_PATH}")


if __name__ == "__main__":
    main()
