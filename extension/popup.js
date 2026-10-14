const API_BASE = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", () => {
  const btnInspectPage = document.getElementById("btnInspectPage");
  const btnPopupAnalyze = document.getElementById("btnPopupAnalyze");
  const popupInputText = document.getElementById("popupInputText");

  btnInspectPage.addEventListener("click", async () => {
    try {
      if (typeof chrome !== "undefined" && chrome.tabs && chrome.tabs.query) {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab && tab.id) {
          const results = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: () => window.getSelection().toString().trim() || document.title
          });

          if (results && results[0] && results[0].result) {
            popupInputText.value = results[0].result;
            analyze(results[0].result, tab.url);
            return;
          }
        }
      }
      // Fallback
      if (popupInputText.value.trim()) {
        analyze(popupInputText.value.trim());
      } else {
        popupInputText.value = "RBI is issuing new 1000 rupee notes with embedded GPS tracking microchip";
        analyze(popupInputText.value);
      }
    } catch (e) {
      console.warn("Chrome scripting unavailable, using input text:", e);
      if (popupInputText.value.trim()) {
        analyze(popupInputText.value.trim());
      }
    }
  });

  btnPopupAnalyze.addEventListener("click", () => {
    const text = popupInputText.value.trim();
    if (!text) {
      alert("Please enter or select text to analyze.");
      return;
    }
    analyze(text);
  });
});

async function analyze(text, url = "") {
  const btn = document.getElementById("btnPopupAnalyze");
  btn.disabled = true;
  btn.textContent = "Analyzing...";

  try {
    const resp = await fetch(`${API_BASE}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, url: url || null })
    });

    if (!resp.ok) {
      throw new Error(`Server returned status ${resp.status}`);
    }

    const data = await resp.json();
    renderPopupResult(data);
  } catch (err) {
    alert("TruthGuard Backend not reachable on http://127.0.0.1:8000.\nPlease ensure uvicorn server is running.\n\nError: " + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Verify Claim";
  }
}

function renderPopupResult(data) {
  const resultCard = document.getElementById("popupResult");
  const badge = document.getElementById("popupBadge");
  const riskNum = document.getElementById("popupRiskNum");
  const riskFill = document.getElementById("popupRiskFill");
  const reasonsList = document.getElementById("popupReasons");
  const matchedBox = document.getElementById("popupMatchedBox");
  const matchedText = document.getElementById("popupMatchedText");

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
  riskFill.style.width = `${Math.min(100, Math.max(5, data.risk_score))}%`;

  if (data.matched_claim) {
    matchedBox.style.display = "block";
    matchedText.textContent = `"${data.matched_claim.claim}" (${(data.breakdown.fact_check.similarity * 100).toFixed(0)}% match, rated ${data.matched_claim.verdict})`;
  } else {
    matchedBox.style.display = "none";
  }

  reasonsList.innerHTML = "";
  (data.reasons || []).slice(0, 3).forEach((r) => {
    const li = document.createElement("li");
    li.textContent = r;
    reasonsList.appendChild(li);
  });
}
