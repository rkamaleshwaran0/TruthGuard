"""
TruthGuard ML Classifier Training Pipeline
Trains a lightweight multilingual TF-IDF + Calibrated Logistic Regression classifier
to assess text credibility / misinformation probability without heavy deep learning overhead.
"""

import csv
import os
import sys
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, accuracy_score, f1_score


def load_dataset(csv_path: str):
    """Load text and binary label (0: Credible, 1: Misinformation) using standard csv module."""
    texts = []
    labels = []
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found at {csv_path}")

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (row.get("text") or "").strip()
            label_val = row.get("label")
            if text and label_val is not None:
                texts.append(text)
                labels.append(int(label_val.strip()))

    return texts, labels


def train_and_save_model(csv_path: str = None, output_path: str = None):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)

    if csv_path is None:
        csv_path = os.path.join(project_root, "data", "train.csv")
    if output_path is None:
        output_path = os.path.join(current_dir, "model.joblib")

    print(f"[TruthGuard ML] Loading training data from {csv_path}...")
    texts, labels = load_dataset(csv_path)
    print(f"[TruthGuard ML] Loaded {len(texts)} samples (Positive/Fake: {sum(labels)}, Reliable: {len(labels) - sum(labels)}).")

    # Lightweight TF-IDF + Logistic Regression pipeline
    # Sublinear TF scaling and character/word n-grams support multilingual scripts
    pipeline = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=4000,
                sublinear_tf=True,
                lowercase=True,
                analyzer="word",
                token_pattern=r"(?u)\b\w+\b"
            ),
        ),
        (
            "clf",
            LogisticRegression(
                C=2.0,
                max_iter=1000,
                solver="lbfgs",
                random_state=42,
                class_weight="balanced"
            ),
        ),
    ])

    # Cross-validation validation
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(pipeline, texts, labels, cv=skf, scoring="f1")
    cv_acc = cross_val_score(pipeline, texts, labels, cv=skf, scoring="accuracy")

    print(f"[TruthGuard ML] 5-Fold CV Accuracy: {cv_acc.mean():.4f} (+/- {cv_acc.std():.4f})")
    print(f"[TruthGuard ML] 5-Fold CV F1 Score: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

    # Fit full model
    pipeline.fit(texts, labels)

    train_preds = pipeline.predict(texts)
    print("\n[TruthGuard ML] Full Training Fit Report:")
    print(classification_report(labels, train_preds, target_names=["Credible (0)", "Misinformation (1)"]))

    # Save artifact
    joblib.dump(pipeline, output_path)
    print(f"[TruthGuard ML] Model successfully serialized to {output_path}")

    return pipeline


if __name__ == "__main__":
    train_and_save_model()
