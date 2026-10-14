"""
TruthGuard Comprehensive Verification Suite
Validates:
1. Strict Evidence-First Decision Rule compliance
2. Multilingual ONNX Semantic Matching (English, Tamil, Hindi)
3. Polarity conflict detection & safeguards against premature flagging
4. Linguistic & ML influence isolation (never triggers 'Potential Fake' on its own)
5. SQLite persistence & FastAPI endpoint integrity
"""

import os
import sys
import time
from fastapi.testclient import TestClient

from services.fusion import (
    fuse_analysis,
    LABEL_RELIABLE,
    LABEL_NEEDS_VERIFICATION,
    LABEL_FAKE
)
from services.fact_check import get_fact_check_matcher
from main import app, init_db, DB_PATH

client = TestClient(app)


def run_tests():
    print("=" * 70)
    print("  TRUTHGUARD — AUTOMATED ARCHITECTURAL & ML VERIFICATION SUITE")
    print("=" * 70)

    passed = 0
    total = 0

    def assert_test(name: str, condition: bool, detail: str = ""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [PASS] Test {total:02d}: {name}")
        else:
            print(f"  [FAIL] Test {total:02d}: {name}")
            if detail:
                print(f"         Details: {detail}")

    # Initialize DB
    init_db()

    # ---------------------------------------------------------
    # TEST 1: Multilingual English Strong Match False -> Potential Fake
    # ---------------------------------------------------------
    res_en_fake = fuse_analysis("RBI is issuing new 1000 rupee notes with GPS tracking chips!")
    assert_test(
        "English Strong Match False -> 'Potential Fake/Misinformation'",
        res_en_fake["label"] == LABEL_FAKE and res_en_fake["risk_score"] >= 80,
        f"Label: {res_en_fake['label']}, Risk: {res_en_fake['risk_score']}"
    )

    # ---------------------------------------------------------
    # TEST 2: Multilingual Tamil Strong Match False -> Potential Fake
    # ---------------------------------------------------------
    res_ta_fake = fuse_analysis("புதிய 2000 ரூபாய் நோட்டில் செயற்கைக்கோள் ஜிபிஎஸ் மைக்ரோசிப் உள்ளது உடனே பகிருங்கள்")
    assert_test(
        "Tamil Strong Match False -> 'Potential Fake/Misinformation'",
        res_ta_fake["label"] == LABEL_FAKE and res_ta_fake["risk_score"] >= 80,
        f"Label: {res_ta_fake['label']}, Sim: {res_ta_fake['breakdown']['fact_check']['similarity']}"
    )

    # ---------------------------------------------------------
    # TEST 3: Multilingual Hindi Strong Match False -> Potential Fake
    # ---------------------------------------------------------
    res_hi_fake = fuse_analysis("2000 के नोट में नैनो जीपीएस चिप लगी है जो जमीन के 120 मीटर नीचे से सिग्नल भेजती है")
    assert_test(
        "Hindi Strong Match False -> 'Potential Fake/Misinformation'",
        res_hi_fake["label"] == LABEL_FAKE and res_hi_fake["risk_score"] >= 80,
        f"Label: {res_hi_fake['label']}, Sim: {res_hi_fake['breakdown']['fact_check']['similarity']}"
    )

    # ---------------------------------------------------------
    # TEST 4: Multilingual English Strong Match True -> Likely Reliable
    # ---------------------------------------------------------
    res_en_true = fuse_analysis("ISRO successfully landed Chandrayaan-3 near lunar south pole")
    assert_test(
        "English Strong Match True -> 'Likely Reliable'",
        res_en_true["label"] == LABEL_RELIABLE and res_en_true["risk_score"] <= 25,
        f"Label: {res_en_true['label']}, Risk: {res_en_true['risk_score']}"
    )

    # ---------------------------------------------------------
    # TEST 5: Multilingual Tamil Strong Match True -> Likely Reliable
    # ---------------------------------------------------------
    res_ta_true = fuse_analysis("சந்திரயான் 3 விண்கலத்தை நிலவின் தென் துருவத்தில் இஸ்ரோ வெற்றிகரமாக தரையிறக்கியது")
    assert_test(
        "Tamil Strong Match True -> 'Likely Reliable'",
        res_ta_true["label"] == LABEL_RELIABLE and res_ta_true["risk_score"] <= 25,
        f"Label: {res_ta_true['label']}, Sim: {res_ta_true['breakdown']['fact_check']['similarity']}"
    )

    # ---------------------------------------------------------
    # TEST 6: Multilingual Hindi Strong Match True -> Likely Reliable
    # ---------------------------------------------------------
    res_hi_true = fuse_analysis("भारत ने चंद्रमा के दक्षिणी ध्रुव पर चंद्रयान 3 की सफल लैंडिंग कराई")
    assert_test(
        "Hindi Strong Match True -> 'Likely Reliable'",
        res_hi_true["label"] == LABEL_RELIABLE and res_hi_true["risk_score"] <= 25,
        f"Label: {res_hi_true['label']}, Sim: {res_hi_true['breakdown']['fact_check']['similarity']}"
    )

    # ---------------------------------------------------------
    # TEST 7: Polarity Conflict Safeguard -> MUST return 'Needs Verification'
    # ---------------------------------------------------------
    res_polarity = fuse_analysis(
        "It is completely false and a debunked rumor that RBI is issuing new 1000 rupee notes with GPS microchips."
    )
    assert_test(
        "Polarity Conflict Safeguard -> 'Needs Verification'",
        res_polarity["label"] == LABEL_NEEDS_VERIFICATION and res_polarity["breakdown"]["fact_check"]["polarity_conflict"] is True,
        f"Label: {res_polarity['label']}, Polarity conflict: {res_polarity['breakdown']['fact_check']['polarity_conflict']}"
    )

    # ---------------------------------------------------------
    # TEST 8: Strict Rule Isolation - Extreme Linguistic Risk WITHOUT fact-check match
    # MUST return 'Needs Verification' and NOT 'Potential Fake'
    # ---------------------------------------------------------
    res_ling_only = fuse_analysis(
        "SHOCKING CONSPIRACY! YOU WON'T BELIEVE THIS MIRACLE CURE! FORWARD TO ALL BEFORE DELETED!!! 🚨🚨🚨"
    )
    assert_test(
        "Extreme Linguistic Risk Alone NEVER triggers 'Potential Fake' -> 'Needs Verification'",
        res_ling_only["label"] == LABEL_NEEDS_VERIFICATION and res_ling_only["breakdown"]["linguistic"]["risk_score"] > 60,
        f"Label: {res_ling_only['label']}, Ling Risk: {res_ling_only['breakdown']['linguistic']['risk_score']}"
    )

    # ---------------------------------------------------------
    # TEST 9: Strict Rule Isolation - Unreliable Domain WITHOUT fact-check match
    # MUST return 'Needs Verification'
    # ---------------------------------------------------------
    res_domain_only = fuse_analysis(
        "Local town council holds weekly meeting to discuss local park maintenance.",
        url="https://www.infowars.com/local-meeting"
    )
    assert_test(
        "Unreliable Domain Alone NEVER triggers 'Potential Fake' -> 'Needs Verification'",
        res_domain_only["label"] == LABEL_NEEDS_VERIFICATION and res_domain_only["breakdown"]["domain"]["tier"] == "unreliable",
        f"Label: {res_domain_only['label']}, Tier: {res_domain_only['breakdown']['domain']['tier']}"
    )

    # ---------------------------------------------------------
    # TEST 10: Unknown / Novel Claim -> 'Needs Verification'
    # ---------------------------------------------------------
    res_novel = fuse_analysis("A new species of glowing mushroom was cataloged in a cloud forest in Costa Rica.")
    assert_test(
        "Unmatched / Novel Claim -> 'Needs Verification'",
        res_novel["label"] == LABEL_NEEDS_VERIFICATION,
        f"Label: {res_novel['label']}"
    )

    # ---------------------------------------------------------
    # TEST 11: FastAPI Endpoint POST /api/analyze
    # ---------------------------------------------------------
    api_resp = client.post("/api/analyze", json={
        "text": "NASA confirms Earth will experience 15 days of total blackout and darkness in December!",
        "url": "https://suspicious-news.xyz/nasa-darkness"
    })
    data = api_resp.json()
    assert_test(
        "API POST /api/analyze returns 200 with complete triage contract",
        api_resp.status_code == 200 and data["label"] == LABEL_FAKE and "id" in data and "risk_score" in data,
        f"Status: {api_resp.status_code}, Label: {data.get('label')}"
    )
    analysis_id = data.get("id")

    # ---------------------------------------------------------
    # TEST 12: FastAPI Endpoint POST /api/feedback & SQLite audit
    # ---------------------------------------------------------
    fb_resp = client.post("/api/feedback", json={
        "analysis_id": analysis_id,
        "verdict": "agree",
        "comment": "Accurately flagged this viral hoax."
    })
    assert_test(
        "API POST /api/feedback records user audit",
        fb_resp.status_code == 200 and fb_resp.json().get("status") == "success"
    )

    # ---------------------------------------------------------
    # TEST 13: FastAPI Endpoint GET /api/history & GET /api/stats
    # ---------------------------------------------------------
    hist_resp = client.get("/api/history")
    stats_resp = client.get("/api/stats")
    stats_data = stats_resp.json()

    assert_test(
        "API GET /api/history and /api/stats reflect database persistence",
        hist_resp.status_code == 200 and
        stats_resp.status_code == 200 and
        stats_data.get("total_analyses", 0) > 0 and
        stats_data.get("feedback_count", 0) > 0,
        f"Stats: {stats_data}"
    )

    print("-" * 70)
    print(f"  VERIFICATION RESULTS: {passed} / {total} Passed ({passed/total*100:.1f}%)")
    print("=" * 70)

    if passed == total:
        print("  ALL ARCHITECTURAL, ML, & PRODUCT REQUIREMENTS VERIFIED!")
        return 0
    else:
        print(f"  {total - passed} TESTS FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
