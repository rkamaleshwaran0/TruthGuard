"""
TruthGuard Fact Check Service
Performs multilingual ONNX semantic similarity matching against verified fact-checks
using FastEmbed (sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2),
with polarity conflict detection and Google Fact Check Tools API support.
"""

import json
import os
import re
import numpy as np
import requests
from fastembed import TextEmbedding

# Negation & Debunking markers for polarity conflict detection
NEGATION_MARKERS = {
    "en": [
        r"\bnot\b", r"\bnever\b", r"\bno\b", r"\bhoax\b", r"\bfake\b", r"\bfalse\b",
        r"\bdebunked\b", r"\brumor\b", r"\bmyth\b", r"\buntrue\b", r"\brefuted\b",
        r"\bdisproven\b", r"\bfabricated\b", r"\bmisleading\b"
    ],
    "ta": [
        r"இல்லை", r"பொய்", r"வதந்தி", r"உண்மை அல்ல", r"தவறு", r"மோசடி", r"நிராகரிப்பு"
    ],
    "hi": [
        r"नहीं", r"झूठ", r"अफवाह", r"गलत", r"फर्जी", r"सत्य नहीं", r"दावा गलत", r"भ्रामक"
    ]
}


class FactCheckMatcher:
    _instance = None

    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.seed_path = os.path.join(self.project_root, "data", "seed.json")
        self.api_key = os.getenv("GOOGLE_FACTCHECK_API_KEY", "").strip()

        print("[FactCheckMatcher] Initializing FastEmbed multilingual ONNX model...")
        self.embed_model = TextEmbedding("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        self.seed_claims = []
        self.seed_embeddings = None
        self._load_seed_database()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_seed_database(self):
        """Loads and embeds verified claims from seed.json into an in-memory normalized matrix."""
        if not os.path.exists(self.seed_path):
            print(f"[FactCheckMatcher] Warning: {self.seed_path} not found.")
            return

        with open(self.seed_path, "r", encoding="utf-8") as f:
            self.seed_claims = json.load(f)

        if not self.seed_claims:
            print("[FactCheckMatcher] No claims found in seed.json.")
            return

        texts_to_embed = [item["claim"] for item in self.seed_claims]
        print(f"[FactCheckMatcher] Embedding {len(texts_to_embed)} seed claims across English, Tamil, and Hindi...")
        raw_embs = list(self.embed_model.embed(texts_to_embed))
        embs_arr = np.array(raw_embs, dtype=np.float32)

        # Normalize for cosine similarity via dot product
        norms = np.linalg.norm(embs_arr, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        self.seed_embeddings = embs_arr / norms
        print(f"[FactCheckMatcher] Pre-computed seed embeddings matrix: {self.seed_embeddings.shape}")

    def detect_polarity_conflict(self, query_text: str, matched_claim_text: str, matched_verdict: str) -> bool:
        """
        Detects if query contains negation/debunking markers while matched claim is in affirmative,
        or vice versa, indicating polarity conflict between user statement and matched claim.
        """
        q_lower = query_text.lower()
        c_lower = matched_claim_text.lower()

        # Check for negation markers in query
        q_has_negation = False
        for lang_markers in NEGATION_MARKERS.values():
            for pat in lang_markers:
                if re.search(pat, q_lower):
                    q_has_negation = True
                    break
            if q_has_negation:
                break

        # Check for negation markers in matched claim
        c_has_negation = False
        for lang_markers in NEGATION_MARKERS.values():
            for pat in lang_markers:
                if re.search(pat, c_lower):
                    c_has_negation = True
                    break
            if c_has_negation:
                break

        # Polarity conflict logic:
        # If the user explicitly negates the claim (e.g., "RBI is NOT issuing 1000 rupee notes")
        # while the seed claim is "RBI is issuing 1000 rupee notes" (verdict: false),
        # the user's statement actually AGREES with the debunk! Labeling the user's text as fake
        # would be a polarity conflict.
        if q_has_negation != c_has_negation:
            return True

        return False

    def query_google_factcheck(self, query_text: str):
        """Optional query to Google Fact Check Tools API."""
        if not self.api_key:
            return None

        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        params = {
            "query": query_text[:200],
            "key": self.api_key,
            "languageCode": "en"
        }
        try:
            resp = requests.get(url, params=params, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                claims = data.get("claims", [])
                if claims:
                    top = claims[0]
                    claim_reviews = top.get("claimReview", [{}])
                    review = claim_reviews[0] if claim_reviews else {}
                    raw_rating = (review.get("textualRating") or "").lower()

                    verdict = "unknown"
                    if any(w in raw_rating for w in ["false", "pants on fire", "fake", "incorrect", "debunked"]):
                        verdict = "false"
                    elif any(w in raw_rating for w in ["true", "correct", "accurate"]):
                        verdict = "true"
                    elif any(w in raw_rating for w in ["mixture", "half true", "misleading", "unproven"]):
                        verdict = "mixed"

                    return {
                        "claim": top.get("text", query_text),
                        "verdict": verdict,
                        "claimant": top.get("claimant", "Unknown"),
                        "publisher": review.get("publisher", {}).get("name", "Google Fact Check Partner"),
                        "url": review.get("url", ""),
                        "review_date": review.get("reviewDate", ""),
                        "source": "google_api"
                    }
        except Exception as e:
            print(f"[FactCheckMatcher] Google Fact Check API error: {e}")
        return None

    def match_claim(self, text: str, claim: str = None) -> dict:
        """
        Finds the highest semantic similarity match for input text/claim.
        Strict Evidence-First Decision Rule:
        - Strong match defined as: similarity >= 0.80 AND verdict in ("true", "false") AND not polarity_conflict
        """
        query_text = (claim if (claim and claim.strip()) else text).strip()
        if not query_text:
            return {
                "matched": False,
                "similarity": 0.0,
                "is_strong_match": False,
                "matched_claim": None,
                "polarity_conflict": False
            }

        # Check Google Fact Check API first if key provided
        google_result = self.query_google_factcheck(query_text)

        # Collect candidate query forms: full text, clean text, and individual sentences
        candidates = [query_text]
        cleaned_main = re.sub(
            r'^(breaking(\s+news)?|viral|alert|shocking|must\s+watch|watch|important|urgent|did\s+you\s+know|fact\s*check)[\s:!\-]+',
            '',
            query_text,
            flags=re.IGNORECASE
        ).strip()
        if cleaned_main and cleaned_main != query_text and len(cleaned_main) >= 12:
            candidates.append(cleaned_main)

        # Split into constituent sentences or clauses
        sentences = [s.strip() for s in re.split(r'[\r\n.!?]+', query_text) if len(s.strip()) >= 15]
        for s in sentences:
            if s not in candidates:
                candidates.append(s)
            s_clean = re.sub(
                r'^(breaking(\s+news)?|viral|alert|shocking|must\s+watch|watch|important|urgent|did\s+you\s+know|fact\s*check)[\s:!\-]+',
                '',
                s,
                flags=re.IGNORECASE
            ).strip()
            if s_clean and s_clean not in candidates and len(s_clean) >= 12:
                candidates.append(s_clean)

        # Generate embeddings for candidate queries in batch using FastEmbed
        cand_embeds = list(self.embed_model.embed(candidates))

        top_match = None
        top_sim = 0.0
        best_candidate = query_text

        if self.seed_embeddings is not None and len(self.seed_claims) > 0:
            for cand_text, cand_raw in zip(candidates, cand_embeds):
                cand_arr = np.array(cand_raw, dtype=np.float32)
                c_norm = np.linalg.norm(cand_arr)
                if c_norm > 0:
                    cand_arr = cand_arr / c_norm
                similarities = np.dot(self.seed_embeddings, cand_arr)
                best_idx = int(np.argmax(similarities))
                sim_val = float(similarities[best_idx])
                if sim_val > top_sim:
                    top_sim = sim_val
                    best_candidate = cand_text
                    top_match = dict(self.seed_claims[best_idx])
                    top_match["source"] = "seed_database"

        # If Google result exists, compare or prioritize
        if google_result and top_sim < 0.80:
            top_match = google_result
            top_sim = 0.85  # Default confidence for direct API match

        if top_match is None or top_sim < 0.60:
            return {
                "matched": False,
                "similarity": round(float(top_sim), 4),
                "is_strong_match": False,
                "matched_claim": None,
                "polarity_conflict": False
            }

        verdict = top_match.get("verdict", "unknown").lower()
        matched_claim_text = top_match.get("claim", "")

        # Check polarity conflict against full query AND best candidate
        conflict_full = self.detect_polarity_conflict(
            query_text=query_text,
            matched_claim_text=matched_claim_text,
            matched_verdict=verdict
        )
        conflict_cand = self.detect_polarity_conflict(
            query_text=best_candidate,
            matched_claim_text=matched_claim_text,
            matched_verdict=verdict
        )
        has_polarity_conflict = conflict_full or conflict_cand

        # STRICT EVIDENCE-FIRST DEFINITION:
        # Strong Match = similarity >= 0.80 AND verdict in ("true", "false") AND not polarity_conflict
        is_strong = (
            top_sim >= 0.80 and
            verdict in ("true", "false") and
            not has_polarity_conflict
        )

        top_match["similarity"] = round(float(top_sim), 4)

        return {
            "matched": True,
            "similarity": round(float(top_sim), 4),
            "verdict": verdict,
            "is_strong_match": is_strong,
            "polarity_conflict": has_polarity_conflict,
            "matched_claim": top_match
        }


def get_fact_check_matcher() -> FactCheckMatcher:
    return FactCheckMatcher.get_instance()
