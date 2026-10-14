"""
TruthGuard — Explainable Real-Time Misinformation Assistant
FastAPI Backend + SQLite + Multilingual Semantic Matcher + Scikit-Learn Classifier
"""

import os
import sqlite3
import uuid
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from services.fusion import fuse_analysis

# Load environment configuration
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "truthguard.db")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Database initialization
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY,
            text TEXT,
            claim TEXT,
            url TEXT,
            label TEXT,
            confidence REAL,
            risk INTEGER,
            created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id TEXT,
            verdict TEXT,
            comment TEXT,
            created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (analysis_id) REFERENCES analyses(id)
        )
    """)
    conn.commit()
    conn.close()


init_db()

# Initialize FastAPI App
app = FastAPI(
    title="TruthGuard API",
    description="Explainable Real-Time Misinformation Triage & Verification API",
    version="1.0.0"
)

# CORS configuration for Chrome Extension and Web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Request & Response Models
class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="Post, article text, or social media forward to evaluate")
    claim: Optional[str] = Field(None, description="Extracted factual claim sentence if distinct from text")
    url: Optional[str] = Field(None, description="Source domain or reference web URL")


class FeedbackRequest(BaseModel):
    analysis_id: str = Field(..., description="UUID of the analysis to give feedback on")
    verdict: str = Field(..., description="User assessment: 'agree', 'disagree', or flag")
    comment: Optional[str] = Field(None, description="Optional user note or source context")


@app.get("/")
def get_root():
    """Serve the interactive web feed UI."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "status": "online",
        "service": "TruthGuard Misinformation Assistant",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.post("/api/analyze")
def analyze_endpoint(req: AnalyzeRequest):
    """
    Main triage endpoint implementing strict evidence-first classification.
    Evaluates semantic claim similarity, linguistic risk, domain reputation, and ML text probability.
    """
    text_content = req.text.strip()
    if not text_content:
        raise HTTPException(status_code=400, detail="Text field cannot be empty.")

    # Execute fusion pipeline
    result = fuse_analysis(text=text_content, claim=req.claim, url=req.url)

    # Persist analysis to SQLite
    analysis_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO analyses (id, text, claim, url, label, confidence, risk)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            analysis_id,
            text_content,
            (req.claim or "").strip(),
            (req.url or "").strip(),
            result["label"],
            result["confidence"],
            result["risk_score"]
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[TruthGuard API] DB write error: {e}")

    result["id"] = analysis_id
    result["created"] = created_at
    result["input_text"] = text_content
    result["input_url"] = req.url or ""
    return result


@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest):
    """Stores user accuracy feedback and comments for continuous audit."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO feedback (analysis_id, verdict, comment)
        VALUES (?, ?, ?)
    """, (req.analysis_id, req.verdict, req.comment or ""))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Feedback submitted successfully."}


@app.get("/api/history")
def get_history(limit: int = 20):
    """Retrieves recent triage analyses from SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, text, claim, url, label, confidence, risk, created
        FROM analyses
        ORDER BY created DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"history": rows}


@app.get("/api/stats")
def get_stats():
    """Returns analytics dashboard metrics: triage distribution, average risk, total analyses."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM analyses")
    total_count = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(risk) FROM analyses")
    avg_risk_row = cursor.fetchone()
    avg_risk = round(avg_risk_row[0], 1) if avg_risk_row and avg_risk_row[0] is not None else 0.0

    cursor.execute("SELECT label, COUNT(*) FROM analyses GROUP BY label")
    label_counts = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("SELECT COUNT(*) FROM feedback")
    feedback_count = cursor.fetchone()[0]

    conn.close()

    return {
        "total_analyses": total_count,
        "average_risk": avg_risk,
        "labels": {
            "Likely Reliable": label_counts.get("Likely Reliable", 0),
            "Needs Verification": label_counts.get("Needs Verification", 0),
            "Potential Fake/Misinformation": label_counts.get("Potential Fake/Misinformation", 0)
        },
        "feedback_count": feedback_count
    }


@app.get("/api/seed-claims")
def get_seed_claims():
    """Returns curated seed examples across English, Tamil, and Hindi for UI testing."""
    from services.fact_check import get_fact_check_matcher
    matcher = get_fact_check_matcher()
    return {"claims": matcher.seed_claims}


# Mount static assets if static folder exists
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
