# TruthGuard 🛡️ — Explainable Real-Time Misinformation Assistant

> An AI-driven, explainable misinformation triage and fact-checking assistant powered by **FastEmbed ONNX Multilingual Embeddings**, **Scikit-Learn NLP**, **FastAPI**, and a **Modern Glassmorphic Web Dashboard**.

---

## 🌟 Key Features

- **Evidence-First Decision Engine**: Prioritizes verified fact-checking evidence over speculative heuristics.
- **Multilingual Semantic Matching**: FastEmbed ONNX embeddings support semantic retrieval across **English**, **Tamil**, and **Hindi**.
- **Polarity Conflict Safeguards**: Prevents debunking or corroboration mismatches by cross-verifying statement stance.
- **Explainable Multi-Signal Fusion**:
  - Semantic Fact-Check Knowledge Base (Seed claims + optional Google Fact Check API)
  - Multilingual TF-IDF + Calibrated Logistic Regression Classifier
  - Rule-Based Linguistic & Sensationalism Analysis
  - Domain & URL Reputation Scoring
- **Full-Featured Modern Web UI**:
  - Real-time text analysis & instant credibility scoring
  - Color-coded risk categorization (`Likely Reliable`, `Needs Verification`, `Potential Fake/Misinformation`)
  - Seed claim selector across multiple languages
  - Telemetry and verification audit trail with user feedback mechanisms
- **Chrome Extension (Manifest V3)**: Inspect claims on social media or news articles in real-time.
- **Automated Verification Suite**: Full test suite covering all decision rules and edge cases with 100% pass rate.

---

## 📁 Project Architecture

```
truthguard/
├── data/
│   ├── seed.json             # Multilingual curated fact-check claims
│   └── train.csv             # Training dataset for ML classifier
├── extension/                # Manifest V3 Chrome Extension
│   ├── manifest.json
│   ├── popup.html
│   └── popup.js
├── ml/
│   ├── model.joblib          # Trained Scikit-Learn TF-IDF model
│   └── train.py              # ML training and evaluation script
├── services/
│   ├── classifier.py         # ML text classification service
│   ├── fact_check.py         # Multilingual FastEmbed ONNX matcher
│   ├── fusion.py             # Evidence-first triage decision engine
│   ├── linguistic.py         # Sensationalism & polarity analysis
│   └── url_rep.py            # Domain reputation checking
├── static/
│   └── index.html            # Premium glassmorphic web dashboard
├── evaluate.py               # Comprehensive 13-point test suite
├── main.py                   # FastAPI application & REST endpoints
├── requirements.txt          # Python dependencies
└── truthguard.db             # Local SQLite database for audit trails
```

---

## 🚀 Quick Start

### 1. Requirements & Prerequisites

- Python 3.10+ (tested with Python 3.14)
- (Optional) Google Fact Check API key

### 2. Installation

Clone the repository and install dependencies:

```bash
git clone <repository_url>
cd truthguard
pip install -r requirements.txt
```

### 3. Environment Configuration (Optional)

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

If you have a Google Fact Check API key:
```env
GOOGLE_FACTCHECK_API_KEY=your_key_here
```

### 4. Running the Application

Launch the FastAPI application:

```bash
python main.py
```

Or using Uvicorn directly:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

- **Web Dashboard**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **API Documentation (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 5. Running the Verification Suite

Run the automated test suite to verify ML models, decision rules, and API endpoints:

```bash
python evaluate.py
```

Expected output:
```
VERIFICATION RESULTS: 13 / 13 Passed (100.0%)
ALL ARCHITECTURAL, ML, & PRODUCT REQUIREMENTS VERIFIED!
```

---

## 🧩 Browser Extension Setup

1. Open Google Chrome or any Chromium-based browser (Edge, Brave).
2. Navigate to `chrome://extensions/`.
3. Enable **Developer mode** in the top right.
4. Click **Load unpacked** and select the `truthguard/extension` folder.
5. The TruthGuard extension icon will appear in your toolbar!

---

## 🛡️ API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the interactive Web Feed UI |
| `POST` | `/api/analyze` | Evaluates claim text, URL, and returns risk analysis |
| `GET` | `/api/seed-claims` | Retrieves curated multilingual test claims |
| `GET` | `/api/stats` | Returns aggregate metrics and label breakdown |
| `GET` | `/api/history` | Fetches recent triage logs |
| `POST` | `/api/feedback` | Records user accuracy feedback & dispute notes |

---

## 📜 License

MIT License. Built for transparency, explainability, and real-time misinformation defense.
