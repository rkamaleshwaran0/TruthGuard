"""
TruthGuard ML Classifier Service
Runs inference on incoming text claims using the pre-trained Scikit-Learn model.
"""

import os
import joblib

_MODEL = None
_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml", "model.joblib")


def get_model():
    """Lazy load the joblib serialized pipeline singleton."""
    global _MODEL
    if _MODEL is None:
        if not os.path.exists(_MODEL_PATH):
            from ml.train import train_and_save_model
            _MODEL = train_and_save_model(output_path=_MODEL_PATH)
        else:
            _MODEL = joblib.load(_MODEL_PATH)
    return _MODEL


def predict_text(text: str) -> dict:
    """
    Predict misinformation probability for given text.
    Returns:
        fake_prob: float [0.0, 1.0]
        is_fake: bool
        confidence: float [0.0, 1.0]
        reasons: list[str]
    """
    if not text or not text.strip():
        return {
            "fake_prob": 0.5,
            "is_fake": False,
            "confidence": 0.0,
            "reasons": []
        }

    model = get_model()
    # Predict probabilities [P(0: reliable), P(1: fake)]
    probs = model.predict_proba([text])[0]
    credible_prob = float(probs[0])
    fake_prob = float(probs[1])
    is_fake = fake_prob >= 0.50
    confidence = round(abs(fake_prob - credible_prob), 3)

    reasons = []
    if fake_prob >= 0.70:
        reasons.append(f"ML text classifier detected high similarity to viral misinformation patterns ({fake_prob * 100:.1f}% risk probability).")
    elif fake_prob <= 0.30:
        reasons.append(f"ML text classifier found stylistic alignment with verified factual reporting ({(1 - fake_prob) * 100:.1f}% credibility probability).")
    else:
        reasons.append("ML text classifier indicates neutral or ambiguous linguistic syntax.")

    return {
        "fake_prob": round(fake_prob, 3),
        "credible_prob": round(credible_prob, 3),
        "is_fake": is_fake,
        "confidence": confidence,
        "reasons": reasons
    }
