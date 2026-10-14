"""
TruthGuard Domain Reputation Service
Analyzes domain reputation, known credible journalism outlets,
satire sites, suspicious TLDs, and deceptive domain formats.
"""

from urllib.parse import urlparse
import re

KNOWN_CREDIBLE = {
    # Fact Checkers & Verifiers
    "boomlive.in", "altnews.in", "factly.in", "vishvasnews.com", "snopes.com",
    "politifact.com", "factcheck.org", "healthfeedback.org", "sciencefeedback.co",
    # Official & Scientific Agencies
    "pib.gov.in", "isro.gov.in", "who.int", "cdc.gov", "nasa.gov", "un.org",
    "nature.com", "sciencemag.org", "nih.gov", "rbi.org.in", "eci.gov.in",
    # Mainstream News Outlets
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "thehindu.com",
    "ndtv.com", "indianexpress.com", "hindustantimes.com", "timesofindia.indiatimes.com",
    "thewire.in", "scroll.in", "dinamalar.com", "dailythanthi.com", "dainikbhaskar.com",
    "amarujala.com", "navbharattimes.indiatimes.com", "nytimes.com", "washingtonpost.com"
}

KNOWN_SATIRE = {
    "theonion.com", "babylonbee.com", "clickhole.com", "theshovel.com.au",
    "fakingnews.firstpost.com", "newsbiscuit.com"
}

KNOWN_UNRELIABLE = {
    "infowars.com", "naturalnews.com", "beforeitsnews.com", "worldnewsdailyreport.com",
    "yournewswire.com", "newspunch.com", "disclose.tv"
}

SUSPICIOUS_TLDS = {
    ".xyz", ".top", ".click", ".buzz", ".work", ".cam", ".country", ".stream", ".loan", ".gq", ".cf", ".ml"
}


def extract_domain(url: str) -> str:
    """Extract normalized base domain from URL."""
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower().strip()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname


def analyze_domain(url: str) -> dict:
    """
    Evaluates domain reputation and returns risk score (0-100) and reasons.
    Does NOT determine classification on its own (strict evidence-first rule).
    """
    if not url or not url.strip():
        return {
            "domain": "",
            "domain_tier": "neutral",
            "domain_risk": 50,
            "reasons": ["No URL provided; domain reputation assessment skipped."]
        }

    domain = extract_domain(url)
    if not domain:
        return {
            "domain": "",
            "domain_tier": "neutral",
            "domain_risk": 50,
            "reasons": ["Invalid or unparseable URL structure."]
        }

    reasons = []
    tier = "neutral"
    risk = 50  # Default neutral score for unknown domains

    # 1. Credible check (exact or parent domain)
    for credible in KNOWN_CREDIBLE:
        if domain == credible or domain.endswith("." + credible):
            tier = "credible"
            risk = 10
            reasons.append(f"Domain '{domain}' is a recognized credible news publisher, scientific institution, or verified fact-checking organization.")
            break

    # 2. Known Satire check
    if tier == "neutral":
        for satire in KNOWN_SATIRE:
            if domain == satire or domain.endswith("." + satire):
                tier = "satire"
                risk = 65
                reasons.append(f"Domain '{domain}' is an established satire or humor publication, not factual reporting.")
                break

    # 3. Known Unreliable check
    if tier == "neutral":
        for unrep in KNOWN_UNRELIABLE:
            if domain == unrep or domain.endswith("." + unrep):
                tier = "unreliable"
                risk = 90
                reasons.append(f"Domain '{domain}' has an established track record of publishing debunked conspiracy theories or unverified claims.")
                break

    # 4. Suspicious TLD / IP address check
    if tier == "neutral":
        # Check IP address as hostname
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", domain):
            tier = "suspicious"
            risk = 85
            reasons.append(f"URL uses a raw IP address ({domain}) instead of an authenticated domain name, typical in phishing or ad-fraud.")
        else:
            for tld in SUSPICIOUS_TLDS:
                if domain.endswith(tld):
                    tier = "suspicious"
                    risk = 75
                    reasons.append(f"Domain uses high-risk top-level domain '{tld}' frequently correlated with disposable spam or phishing sites.")
                    break

    # 5. Typosquatting / Deceptive brand in subdomain
    if tier in ("neutral", "suspicious"):
        for trusted_brand in ["bbc", "reuters", "who", "rbi", "pib", "isro", "gov", "apple", "google"]:
            if trusted_brand in domain and not any(domain.endswith(t) for t in KNOWN_CREDIBLE):
                tier = "suspicious"
                risk = max(risk, 80)
                reasons.append(f"Domain name contains trusted brand pattern '{trusted_brand}' without matching official domain registration (potential brand impersonation).")
                break

    if tier == "neutral" and not reasons:
        reasons.append(f"Domain '{domain}' is an unranked independent web domain; source authority requires verification.")

    return {
        "domain": domain,
        "domain_tier": tier,
        "domain_risk": risk,
        "reasons": reasons
    }
