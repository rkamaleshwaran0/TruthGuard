"""
TruthGuard Decision Fusion Engine
Implements the Strict Evidence-First Decision Rule and assembles
explainable analysis combining fact-checking, linguistic risk,
domain reputation, and machine learning probabilities.
"""

from typing import Optional
from services.fact_check import get_fact_check_matcher
from services.linguistic import analyze_linguistics
from services.url_rep import analyze_domain
from services.classifier import predict_text


LABEL_RELIABLE = "Likely Reliable"
LABEL_NEEDS_VERIFICATION = "Needs Verification"
LABEL_FAKE = "Potential Fake/Misinformation"


def fuse_analysis(text: str, claim: Optional[str] = None, url: Optional[str] = None) -> dict:
    """
    Executes full multi-modal analysis pipeline and returns unified explainable assessment.
    
    Strict Evidence-First Decision Rule:
    1. Strong Match = similarity >= 0.80 AND verdict in ("true", "false") AND not polarity_conflict
    2. Strong Match + "false" -> "Potential Fake/Misinformation"
    3. Strong Match + "true" -> "Likely Reliable"
    4. ALL OTHER CASES -> "Needs Verification"
    5. Linguistic risk, ML probability, and domain reputation only adjust the numerical
       risk_score (0-100) and reasons list. They NEVER trigger "Potential Fake/Misinformation" on their own.
    """
    clean_text = (text or "").strip()
    clean_claim = (claim or "").strip()
    primary_text = clean_claim if clean_claim else clean_text

    # 1. Fact-check semantic similarity matching (Multilingual ONNX FastEmbed)
    matcher = get_fact_check_matcher()
    fact_result = matcher.match_claim(text=clean_text, claim=clean_claim)

    # 2. Linguistic and stylometric analysis
    ling_result = analyze_linguistics(clean_text)

    # 3. Domain reputation analysis
    url_result = analyze_domain(url or "")

    # 4. ML Text Classifier inference
    ml_result = predict_text(clean_text)

    # Decision Logic: Strict Evidence-First
    is_strong = fact_result.get("is_strong_match", False)
    verdict = fact_result.get("verdict", "unknown")
    has_polarity_conflict = fact_result.get("polarity_conflict", False)
    similarity = fact_result.get("similarity", 0.0)
    matched_claim_data = fact_result.get("matched_claim")

    reasons = []

    if is_strong and verdict == "false":
        label = LABEL_FAKE
        # Strong match to a debunked claim: Base risk 88, adjusted by signals up to 99
        base_risk = 88.0
        signal_boost = (ling_result["risk_score"] * 0.06) + (ml_result["fake_prob"] * 6.0)
        risk_score = int(min(99, max(85, round(base_risk + signal_boost))))
        confidence = round(min(0.98, max(0.85, similarity)), 2)

        publisher = (matched_claim_data or {}).get("publisher", "Independent Fact-Checker")
        ref_url = (matched_claim_data or {}).get("url", "")
        reasons.append(
            f"Strong Fact-Check Match: Debunked as FALSE by {publisher} with {similarity * 100:.1f}% semantic similarity."
        )
        if ref_url:
            reasons.append(f"Fact-Check Source: {ref_url}")

    elif is_strong and verdict == "true":
        label = LABEL_RELIABLE
        # Strong match to an authenticated claim: Base risk 10
        risk_score = int(max(5, min(20, round(15.0 - (similarity - 0.80) * 25.0))))
        confidence = round(min(0.99, max(0.88, similarity)), 2)

        publisher = (matched_claim_data or {}).get("publisher", "Official Agency / Fact-Checker")
        ref_url = (matched_claim_data or {}).get("url", "")
        reasons.append(
            f"Strong Fact-Check Match: Verified as TRUE by {publisher} with {similarity * 100:.1f}% semantic similarity."
        )
        if ref_url:
            reasons.append(f"Verified Reference Source: {ref_url}")

    else:
        # ALL OTHER CASES MUST RETURN "Needs Verification"
        label = LABEL_NEEDS_VERIFICATION

        # Calculate numerical risk score (0-100) based on ML, linguistics, and domain
        ml_weight = ml_result["fake_prob"] * 40.0
        ling_weight = (ling_result["risk_score"] / 100.0) * 35.0
        url_weight = (url_result["domain_risk"] / 100.0) * 25.0
        combined_calc = ml_weight + ling_weight + url_weight

        # If weak match to false claim (0.65-0.79), slightly lift risk score
        if matched_claim_data and verdict == "false" and 0.65 <= similarity < 0.80:
            combined_calc = max(combined_calc, similarity * 75.0)

        # In "Needs Verification", risk score ranges informatively between 15 and 85
        risk_score = int(max(15, min(85, round(combined_calc))))
        confidence = round(0.55 + abs(risk_score - 50) / 150.0, 2)

        # Explain why it was triaged to "Needs Verification"
        if has_polarity_conflict:
            reasons.append(
                f"Polarity Conflict Detected: Claim semantically relates to a known fact-check ({similarity * 100:.1f}% match), "
                "but contains opposing negation or debunking phrasing. Flagged for human verification to prevent false misidentification."
            )
        elif 0.70 <= similarity < 0.80:
            publisher = (matched_claim_data or {}).get("publisher", "Fact-Checker")
            reasons.append(
                f"Partial Semantic Match ({similarity * 100:.1f}%): Correlates with claims reviewed by {publisher}, "
                "but falls below the strict 80% evidence threshold required for automated labeling."
            )
        elif verdict in ("mixed", "unknown") and similarity >= 0.70:
            reasons.append(
                f"Ambiguous Evidence: Related fact-checks categorized the claim as '{verdict}' or nuanced; independent context required."
            )
        else:
            reasons.append(
                "No conclusive fact-check verification exists in accredited databases for this specific claim."
            )

    # Append secondary explainability factors
    for r in ling_result.get("reasons", []):
        if "calm, neutral" not in r:
            reasons.append(f"Linguistic Signal: {r}")

    for r in url_result.get("reasons", []):
        if "assessment skipped" not in r:
            reasons.append(f"Domain Reputation: {r}")

    for r in ml_result.get("reasons", []):
        reasons.append(f"ML Classifier: {r}")

    # Color tokens for UI consistency
    color_map = {
        LABEL_RELIABLE: "green",
        LABEL_NEEDS_VERIFICATION: "yellow",
        LABEL_FAKE: "red"
    }

    return {
        "label": label,
        "color": color_map[label],
        "risk_score": risk_score,
        "confidence": confidence,
        "matched_claim": matched_claim_data if fact_result.get("matched") else None,
        "breakdown": {
            "fact_check": {
                "matched": fact_result.get("matched", False),
                "similarity": similarity,
                "is_strong_match": is_strong,
                "polarity_conflict": has_polarity_conflict,
                "verdict": verdict
            },
            "linguistic": {
                "risk_score": ling_result["risk_score"],
                "flags": ling_result["flags"]
            },
            "domain": {
                "domain": url_result["domain"],
                "tier": url_result["domain_tier"],
                "risk_score": url_result["domain_risk"]
            },
            "ml_classifier": {
                "fake_prob": ml_result["fake_prob"],
                "credible_prob": ml_result["credible_prob"],
                "is_fake": ml_result["is_fake"]
            }
        },
        "reasons": reasons
    }
