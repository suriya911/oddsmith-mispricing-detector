"""
VerbaTrust FastAPI application.

Endpoints:
  POST /analyze           → CredibilityReport  (trigger analysis)
  GET  /report/{company}  → last stored report
  GET  /transcript/{company}/{quarter}  → text + hedging spans
  GET  /activity/{job_id} → SSE stream of agent steps
  GET  /graph/search      → free-form Cognee graph query
  GET  /health            → liveness check
"""
from __future__ import annotations
import asyncio
import json
import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from models import CredibilityReport, AnalyzeRequest
import agent
import memory

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="VerbaTrust", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory report cache (company → report)
_reports: dict[str, CredibilityReport] = {}
# Job tracking (job_id → status)
_jobs: dict[str, dict] = {}

_executor = ThreadPoolExecutor(max_workers=4)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/analyze", response_model=dict)
async def analyze(req: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Kick off an analysis job. Returns immediately with a job_id."""
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {"status": "running", "company": req.company, "started_at": time.time()}
    background_tasks.add_task(_run_analysis, job_id, req.company, req.mode)
    return {"job_id": job_id, "status": "running", "company": req.company}


def _run_analysis(job_id: str, company: str, mode: str) -> None:
    try:
        report = agent.analyze(company, mode)
        _reports[company] = report
        _jobs[job_id] = {
            **_jobs.get(job_id, {}),
            "status": "completed",
            "report": report.model_dump(),
            "finished_at": time.time(),
        }
    except Exception as e:
        logger.error(f"Analysis failed for {company}: {e}", exc_info=True)
        _jobs[job_id] = {
            **_jobs.get(job_id, {}),
            "status": "error",
            "error": str(e),
        }


@app.get("/report/{company}", response_model=CredibilityReport)
def get_report(company: str):
    report = _reports.get(company.upper())
    if not report:
        # Try loading from local memory store
        quarters = memory.recall_all(company.upper())
        if quarters:
            raise HTTPException(
                status_code=404,
                detail=f"Report not yet generated. POST /analyze first. Found {len(quarters)} stored quarter(s) in memory.",
            )
        raise HTTPException(status_code=404, detail=f"No report for {company}. POST /analyze first.")
    return report


class TranscriptHighlight(BaseModel):
    text: str
    hedging_spans: list[dict]
    hedging_density: float
    quarter: str
    company: str


@app.get("/transcript/{company}/{quarter}", response_model=TranscriptHighlight)
def get_transcript(company: str, quarter: str):
    all_quarters = memory.recall_all(company.upper())
    qd = next((q for q in all_quarters if q.quarter.upper() == quarter.upper()), None)
    if not qd:
        raise HTTPException(status_code=404, detail=f"Transcript not found for {company} {quarter}")

    spans = _build_hedging_spans(qd.raw_transcript, qd.hedging_markers)
    return TranscriptHighlight(
        text=qd.raw_transcript,
        hedging_spans=spans,
        hedging_density=qd.hedging_density,
        quarter=qd.quarter,
        company=qd.company,
    )


@app.get("/activity/{job_id}")
async def activity_stream(job_id: str):
    """Server-Sent Events stream of live agent activity log."""
    async def _event_gen() -> AsyncGenerator[str, None]:
        sent_count = 0
        for _ in range(120):  # max 60 s
            job = _jobs.get(job_id, {})
            log = agent.get_activity_log()
            while sent_count < len(log):
                line = log[sent_count]
                yield f"data: {json.dumps({'step': line})}\n\n"
                sent_count += 1

            if job.get("status") in ("completed", "error"):
                payload = {"done": True, "status": job["status"]}
                if job.get("status") == "completed":
                    payload["score"] = job.get("report", {}).get("score")
                elif job.get("error"):
                    payload["error"] = job["error"]
                yield f"data: {json.dumps(payload)}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(_event_gen(), media_type="text/event-stream")


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/graph/search")
def graph_search(q: str):
    """Free-form Cognee graph query for live demo Q&A."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="q parameter required")
    answer = memory.search_graph(q)
    return {"query": q, "answer": answer}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _build_hedging_spans(text: str, markers: list[str]) -> list[dict]:
    import re
    spans: list[dict] = []
    for marker in markers:
        for m in re.finditer(re.escape(marker), text, re.IGNORECASE):
            spans.append({"start": m.start(), "end": m.end(), "marker": marker})
    return spans
