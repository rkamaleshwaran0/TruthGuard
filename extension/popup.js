const API_BASE = "http://127.0.0.1:8000";

let currentAnalysisId = null;
let currentTabUrl = "";

const KNOWN_CREDIBLE_DOMAINS = [
  "boomlive.in", "altnews.in", "factly.in", "vishvasnews.com", "snopes.com",
  "politifact.com", "factcheck.org", "healthfeedback.org", "sciencefeedback.co",
  "pib.gov.in", "isro.gov.in", "who.int", "cdc.gov", "nasa.gov", "un.org",
  "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "thehindu.com",
  "ndtv.com", "indianexpress.com", "hindustantimes.com", "timesofindia.indiatimes.com",
  "nytimes.com", "washingtonpost.com", "theguardian.com", "cnn.com", "bloomberg.com"
];

const KNOWN_UNRELIABLE_DOMAINS = [
  "infowars.com", "naturalnews.com", "beforeitsnews.com", "worldnewsdailyreport.com",
  "yournewswire.com", "newspunch.com", "disclose.tv"
];

const KNOWN_SATIRE_DOMAINS = [
  "theonion.com", "babylonbee.com", "clickhole.com", "theshovel.com.au"
];

document.addEventListener("DOMContentLoaded", async () => {
  const btnInspectPage = document.getElementById("btnInspectPage");
  const btnPopupAnalyze = document.getElementById("btnPopupAnalyze");
  const popupInputText = document.getElementById("popupInputText");
  const tabDomainText = document.getElementById("tabDomainText");
  const tabDomainBadge = document.getElementById("tabDomainBadge");
  const btnFbAgree = document.getElementById("btnFbAgree");
  const btnFbFlag = document.getElementById("btnFbFlag");

  // 1. Initialize Active Tab domain info
  await initActiveTab(tabDomainText, tabDomainBadge);

  // 2. Preset Pills Click Listener
  document.querySelectorAll(".preset-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      const claim = pill.getAttribute("data-claim");
      if (claim) {
        popupInputText.value = claim;
        analyze(claim, currentTabUrl);
      }
    });
  });

  // 3. Inspect Current Page Button Listener
  btnInspectPage.addEventListener("click", async () => {
    try {
      if (typeof chrome !== "undefined" && chrome.tabs && chrome.tabs.query) {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab && tab.id) {
          currentTabUrl = tab.url || "";
          const results = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: extractPageClaim
          });

          if (results && results[0] && results[0].result) {
            const extracted = results[0].result;
            popupInputText.value = extracted;
            analyze(extracted, currentTabUrl);
            return;
          }
        }
      }

      // Fallback if not inside extension context or script failed
      if (popupInputText.value.trim()) {
        analyze(popupInputText.value.trim(), currentTabUrl);
      } else {
        popupInputText.value = "RBI is issuing new 1000 rupee notes with embedded GPS tracking microchip";
        analyze(popupInputText.value, currentTabUrl);
      }
    } catch (e) {
      console.warn("Script execution fallback:", e);
      if (popupInputText.value.trim()) {
        analyze(popupInputText.value.trim(), currentTabUrl);
      }
    }
  });

  // 4. Manual Analyze Button
  btnPopupAnalyze.addEventListener("click", () => {
    const text = popupInputText.value.trim();
    if (!text) {
      alert("Please enter or select text to analyze.");
      return;
    }
    analyze(text, currentTabUrl);
  });

  // 5. User Feedback Listeners
  if (btnFbAgree) {
    btnFbAgree.addEventListener("click", () => sendFeedback("agree"));
  }
  if (btnFbFlag) {
    btnFbFlag.addEventListener("click", () => sendFeedback("flag"));
  }
});

/**
 * Intelligent in-page extraction executed inside the active tab.
 * Extracts user selection or cleans headlines/meta tags.
 */
function extractPageClaim() {
  // 1. Priority: User text selection
  const selection = window.getSelection().toString().trim();
  if (selection && selection.length > 10) {
    return selection;
  }

  // 2. OpenGraph / Twitter meta titles or main H1
  let title = "";
  const ogTitle = document.querySelector('meta[property="og:title"]');
  const twTitle = document.querySelector('meta[name="twitter:title"]');
  const h1 = document.querySelector("h1");

  if (ogTitle && ogTitle.content) {
    title = ogTitle.content.trim();
  } else if (twTitle && twTitle.content) {
    title = twTitle.content.trim();
  } else if (h1 && h1.innerText) {
    title = h1.innerText.trim();
  } else {
    title = document.title || "";
  }

  // Clean trailing site branding suffixes (e.g., " | BBC News", " - The Hindu")
  title = title.replace(/\s*([|\-–—•:]\s*(BBC News|The Hindu|NDTV|Times of India|India Today|Reuters|CNN|The New York Times|The Guardian|Snopes|AltNews|BoomLive|YouTube|Facebook|Twitter|X|Reddit|Wikipedia).*)$/i, "").trim();

  // 3. Lead summary or description
  const ogDesc = document.querySelector('meta[property="og:description"]');
  const metaDesc = document.querySelector('meta[name="description"]');
  let desc = "";
  if (ogDesc && ogDesc.content) {
    desc = ogDesc.content.trim();
  } else if (metaDesc && metaDesc.content) {
    desc = metaDesc.content.trim();
  }

  if (desc && desc.length > 20 && !title.includes(desc)) {
    return `${title}. ${desc}`;
  }

  return title;
}

/**
 * Identify and display current tab domain and credibility tier
 */
async function initActiveTab(domainEl, badgeEl) {
  try {
    if (typeof chrome !== "undefined" && chrome.tabs && chrome.tabs.query) {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.url) {
        currentTabUrl = tab.url;
        const urlObj = new URL(tab.url);
        let domain = urlObj.hostname.replace(/^www\./, "");
        domainEl.textContent = domain;

        // Check domain tier
        const isCredible = KNOWN_CREDIBLE_DOMAINS.some(d => domain === d || domain.endsWith("." + d));
        const isUnreliable = KNOWN_UNRELIABLE_DOMAINS.some(d => domain === d || domain.endsWith("." + d));
        const isSatire = KNOWN_SATIRE_DOMAINS.some(d => domain === d || domain.endsWith("." + d));

        if (isCredible) {
          badgeEl.textContent = "Accredited Source";
          badgeEl.className = "domain-badge badge-credible";
        } else if (isUnreliable) {
          badgeEl.textContent = "Flagged Unreliable";
          badgeEl.className = "domain-badge badge-unreliable";
        } else if (isSatire) {
          badgeEl.textContent = "Satire Outlet";
          badgeEl.className = "domain-badge badge-satire";
        } else {
          badgeEl.textContent = "Web Source";
          badgeEl.className = "domain-badge badge-neutral";
        }
        return;
      }
    }
  } catch (e) {
    console.log("Tab domain lookup skipped:", e);
  }

  if (domainEl) domainEl.textContent = "Offline / Localhost";
  if (badgeEl) {
    badgeEl.textContent = "Standby";
    badgeEl.className = "domain-badge badge-neutral";
  }
}

/**
 * Execute claim analysis through TruthGuard API
 */
async function analyze(text, url = "") {
  const btn = document.getElementById("btnPopupAnalyze");
  btn.disabled = true;
  btn.textContent = "Evaluating Signals...";

  try {
    const resp = await fetch(`${API_BASE}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, url: url || null })
    });

    if (!resp.ok) {
      throw new Error(`Server returned HTTP ${resp.status}`);
    }

    const data = await resp.json();
    currentAnalysisId = data.id;
    renderPopupResult(data);
  } catch (err) {
    alert("TruthGuard Backend not reachable on http://127.0.0.1:8000.\nPlease ensure uvicorn server is running.\n\nError: " + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Verify Claim";
  }
}

/**
 * Render comprehensive triage and multi-signal breakdown
 */
function renderPopupResult(data) {
  const resultCard = document.getElementById("popupResult");
  const badge = document.getElementById("popupBadge");
  const riskNum = document.getElementById("popupRiskNum");
  const riskFill = document.getElementById("popupRiskFill");
  const reasonsList = document.getElementById("popupReasons");

  // Signals
  const sigFactCheck = document.getElementById("sigFactCheck");
  const sigDomain = document.getElementById("sigDomain");
  const sigLinguistic = document.getElementById("sigLinguistic");
  const sigML = document.getElementById("sigML");

  // Matched Box
  const matchedBox = document.getElementById("popupMatchedBox");
  const matchedText = document.getElementById("popupMatchedText");
  const matchedLink = document.getElementById("popupMatchedLink");

  // Reset feedback
  const fbBtnGroup = document.getElementById("fbBtnGroup");
  const fbSuccess = document.getElementById("fbSuccess");
  const fbPrompt = document.getElementById("fbPrompt");
  if (fbBtnGroup) fbBtnGroup.style.display = "flex";
  if (fbSuccess) fbSuccess.style.display = "none";
  if (fbPrompt) fbPrompt.style.display = "inline";

  resultCard.style.display = "block";
  badge.textContent = data.label;
  badge.className = "triage-badge";

  if (data.label === "Likely Reliable") {
    badge.classList.add("badge-reliable");
    riskFill.style.background = "#10b981";
  } else if (data.label === "Potential Fake/Misinformation") {
    badge.classList.add("badge-fake");
    riskFill.style.background = "#ef4444";
  } else {
    badge.classList.add("badge-warning");
    riskFill.style.background = "#f59e0b";
  }

  riskNum.textContent = `Risk: ${data.risk_score}/100`;
  riskFill.style.width = `${Math.min(100, Math.max(6, data.risk_score))}%`;

  // 1. Fact-Check Signal
  const fc = (data.breakdown && data.breakdown.fact_check) || {};
  if (fc.matched && data.matched_claim) {
    const pct = (fc.similarity * 100).toFixed(0);
    const pub = data.matched_claim.publisher || "Fact-Checker";
    sigFactCheck.textContent = `${pct}% Match (${pub})`;
    sigFactCheck.style.color = fc.verdict === "false" ? "#f87171" : "#4ade80";
  } else {
    sigFactCheck.textContent = "No verified match";
    sigFactCheck.style.color = "var(--text-muted)";
  }

  // 2. Domain Signal
  const dom = (data.breakdown && data.breakdown.domain) || {};
  if (dom.domain) {
    sigDomain.textContent = `${dom.domain} (${dom.tier})`;
    sigDomain.style.color = dom.tier === "credible" ? "#4ade80" : (dom.tier === "unreliable" ? "#f87171" : "var(--text-main)");
  } else {
    sigDomain.textContent = "No URL Provided";
    sigDomain.style.color = "var(--text-muted)";
  }

  // 3. Linguistic Signal
  const ling = (data.breakdown && data.breakdown.linguistic) || {};
  if (ling.flags && ling.flags.length > 0) {
    sigLinguistic.textContent = ling.flags.join(", ");
    sigLinguistic.style.color = "#fbbf24";
  } else {
    sigLinguistic.textContent = "Neutral & Objective";
    sigLinguistic.style.color = "#4ade80";
  }

  // 4. ML Model Signal
  const ml = (data.breakdown && data.breakdown.ml_classifier) || {};
  if (ml.fake_prob !== undefined) {
    const fakePct = (ml.fake_prob * 100).toFixed(0);
    sigML.textContent = ml.is_fake ? `${fakePct}% Fake Risk` : `${(100 - fakePct)}% Credible Syntax`;
    sigML.style.color = ml.is_fake ? "#f87171" : "#4ade80";
  }

  // Matched Claim Details
  if (data.matched_claim) {
    matchedBox.style.display = "block";
    matchedText.textContent = `"${data.matched_claim.claim}" — Rated ${data.matched_claim.verdict.toUpperCase()} by ${data.matched_claim.publisher || "Fact Check Organization"}.`;
    if (data.matched_claim.url) {
      matchedLink.style.display = "inline-block";
      matchedLink.href = data.matched_claim.url;
    } else {
      matchedLink.style.display = "none";
    }
  } else {
    matchedBox.style.display = "none";
  }

  // Reasons list
  reasonsList.innerHTML = "";
  (data.reasons || []).slice(0, 4).forEach((r) => {
    const li = document.createElement("li");
    li.textContent = r;
    reasonsList.appendChild(li);
  });
}

/**
 * Submit user feedback to TruthGuard audit log
 */
async function sendFeedback(verdict) {
  if (!currentAnalysisId) return;

  try {
    const resp = await fetch(`${API_BASE}/api/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        analysis_id: currentAnalysisId,
        verdict: verdict,
        comment: "Extension Quick Feedback"
      })
    });

    if (resp.ok) {
      const fbBtnGroup = document.getElementById("fbBtnGroup");
      const fbSuccess = document.getElementById("fbSuccess");
      const fbPrompt = document.getElementById("fbPrompt");
      if (fbBtnGroup) fbBtnGroup.style.display = "none";
      if (fbPrompt) fbPrompt.style.display = "none";
      if (fbSuccess) fbSuccess.style.display = "inline";
    }
  } catch (e) {
    console.warn("Feedback submission error:", e);
  }
}
