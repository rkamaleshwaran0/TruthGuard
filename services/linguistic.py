"""
TruthGuard Linguistic & Stylometric Analysis Service
Evaluates sensationalism, urgency, conspiracy markers, all-caps shouting,
and aggressive punctuation in English, Tamil, and Hindi.
"""

import re
import unicodedata

# English heuristics
SENSATIONAL_EN = [
    r"\bshocking\b", r"\bunbelievable\b", r"\byou won'?t believe\b", r"\bsecret they don'?t want you to know\b",
    r"\bmust watch before (?:deleted|it'?s taken down)\b", r"\bmiracle cure\b", r"\bdoctors (?:are terrified|hate this)\b",
    r"\b100% cure\b", r"\bbig pharma\b", r"\bsecret plot\b", r"\bconspiracy\b", r"\brevealed\b",
    r"\bsecret leaked\b", r"\bloophole\b", r"\bdestroys all\b", r"\binstant death\b"
]

URGENCY_EN = [
    r"\bforward to all\b", r"\bshare before (?:deleted|banned)\b", r"\burgent warning\b", r"\bact now\b",
    r"\bspread everywhere\b", r"\bemergency alert\b", r"\bdo not pick calls\b", r"\bdo not eat\b",
    r"\bshare to save lives\b", r"\bbreaking\b", r"\balert\b"
]

# Tamil heuristics
SENSATIONAL_TA = [
    r"அதிர்ச்சி(?: செய்தி)?", r"அதிசய(?:ம்| மருத்துவம்)", r"ரகசியம்", r"மருத்துவர்கள் மறைக்கும் உண்மை",
    r"உடனே பாருங்கள்", r"100% குணமாகும்", r"வியக்கும்", r"மர்மம்", r"பரபரப்பு", r"முற்றிலும் குணப்படுத்தும்"
]

URGENCY_TA = [
    r"உடனே பகிரவும்", r"அனைவருக்கும் அனுப்பவும்", r"அவசர எச்சரிக்கை", r"உடனே பகிருங்கள்",
    r"உயிரை காப்பாற்ற", r"தாமதிக்காமல் பகிருங்கள்", r"எச்சரிக்கை"
]

# Hindi heuristics
SENSATIONAL_HI = [
    r"धमाका", r"चौंकाने वाला", r"चमत्कारी(?: नुस्खा)?", r"गुप्त रहस्य", r"डॉक्टर भी हैरान",
    r"बड़ा खुलासा", r"सनसनीखेज", r"हैरान कर देगा", r"जड़ से खत्म"
]

URGENCY_HI = [
    r"तुरंत शेयर करें", r"सबको बताएं", r"जल्दी फॉरवर्ड करें", r"चेतावनी", r"खतरे की घंटी",
    r"सावधान", r"हर भारतीय शेयर करे", r"तुरंत फॉरवर्ड करें"
]

PANIC_EMOJIS = set(["🚨", "⚠️", "😱", "💥", "🛑", "🔥", "⚡", "‼️", "❌", "📢", "💣"])


def analyze_linguistics(text: str) -> dict:
    """
    Computes linguistic risk score (0-100) and detailed explainability reasons.
    Does NOT determine classification on its own (strict evidence-first rule).
    """
    if not text or not text.strip():
        return {
            "risk_score": 0,
            "sensationalism_score": 0,
            "urgency_score": 0,
            "stylometry_score": 0,
            "flags": [],
            "reasons": []
        }

    clean_text = text.strip()
    lower_text = clean_text.lower()

    flags = []
    reasons = []

    sensational_hits = 0
    urgency_hits = 0

    # 1. Sensationalism checks (EN, TA, HI)
    for pat in SENSATIONAL_EN:
        if re.search(pat, lower_text):
            sensational_hits += 1
    for pat in SENSATIONAL_TA:
        if re.search(pat, clean_text):
            sensational_hits += 1
    for pat in SENSATIONAL_HI:
        if re.search(pat, clean_text):
            sensational_hits += 1

    # 2. Urgency & Call to action checks (EN, TA, HI)
    for pat in URGENCY_EN:
        if re.search(pat, lower_text):
            urgency_hits += 1
    for pat in URGENCY_TA:
        if re.search(pat, clean_text):
            urgency_hits += 1
    for pat in URGENCY_HI:
        if re.search(pat, clean_text):
            urgency_hits += 1

    # 3. Stylometry: ALL CAPS check
    latin_chars = [c for c in clean_text if "A" <= c <= "Z" or "a" <= c <= "z"]
    caps_ratio = 0.0
    if len(latin_chars) >= 15:
        upper_count = sum(1 for c in latin_chars if c.isupper())
        caps_ratio = upper_count / len(latin_chars)

    caps_flag = caps_ratio >= 0.35

    # 4. Punctuation anomalies (!!!, ???)
    exclamation_streak = bool(re.search(r"!{2,}", clean_text))
    question_streak = bool(re.search(r"\?{2,}", clean_text))
    total_exclamations = clean_text.count("!")

    # 5. Emoji density
    emoji_count = sum(1 for ch in clean_text if ch in PANIC_EMOJIS)

    # Scoring breakdown
    sens_score = min(100, sensational_hits * 30)
    urg_score = min(100, urgency_hits * 35)

    style_score = 0
    if caps_flag:
        style_score += 40
    if exclamation_streak or total_exclamations >= 3:
        style_score += 35
    if question_streak:
        style_score += 15
    if emoji_count >= 2:
        style_score += min(30, emoji_count * 15)
    style_score = min(100, style_score)

    # Combined linguistic risk (0 to 100)
    composite_risk = int(min(100, (sens_score * 0.40) + (urg_score * 0.40) + (style_score * 0.20)))

    # Explainability reasons
    if sensational_hits > 0:
        flags.append("SENSATIONAL_LANGUAGE")
        reasons.append(f"Sensational or miracle-cure keywords detected ({sensational_hits} matches).")

    if urgency_hits > 0:
        flags.append("URGENT_CALL_TO_ACTION")
        reasons.append(f"High-urgency sharing prompts or panic hooks detected ('forward to all' / 'share before deleted').")

    if caps_flag:
        flags.append("EXCESSIVE_CAPITALIZATION")
        reasons.append(f"Excessive ALL CAPS text detected ({caps_ratio * 100:.0f}% uppercase ratio), indicating aggressive tone.")

    if exclamation_streak or total_exclamations >= 3:
        flags.append("EXCESSIVE_EXCLAMATION")
        reasons.append(f"Multiple consecutive exclamation marks detected ({total_exclamations} '!'), common in viral bait.")

    if emoji_count >= 2:
        flags.append("PANIC_EMOJIS")
        reasons.append(f"High concentration of alarm/panic emojis ({emoji_count} symbols).")

    if composite_risk == 0:
        reasons.append("Linguistic syntax is calm, neutral, and objective.")

    return {
        "risk_score": composite_risk,
        "sensationalism_score": sens_score,
        "urgency_score": urg_score,
        "stylometry_score": style_score,
        "flags": flags,
        "reasons": reasons
    }
