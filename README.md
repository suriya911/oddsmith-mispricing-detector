# VerbaTrust — Management Credibility Engine

> *"Management always sounds confident. Our engine reads what they stopped saying."*

[![CI](https://github.com/suriya911/oddsmith-mispricing-detector/actions/workflows/ci.yml/badge.svg)](https://github.com/suriya911/oddsmith-mispricing-detector/actions/workflows/ci.yml)
[![Deploy](https://github.com/suriya911/oddsmith-mispricing-detector/actions/workflows/deploy.yml/badge.svg)](https://github.com/suriya911/oddsmith-mispricing-detector/actions/workflows/deploy.yml)

VerbaTrust scores management credibility by diffing earnings-call language against prior quarters (stored in a **Cognee** knowledge graph) and cross-checking the optimistic narrative against live web signals scraped in real time via **Bright Data**. Language scoring runs through **AI/ML API**; bulk transcript summarization uses **Featherless AI**.

**Output:** A Credibility Score (0–100) with every deducted point linked to an evidence quote and a source URL.

---

## Live Demo

Default demo company: **NMBS** (Nimbus Logistics — fictional, copyright-clean, no paywall issues).

| Quarter | Score | Delta | Headline |
|---------|-------|-------|---------|
| Q1 2026 | 86 / 100 | — | Confident tone, firm commitments, specific KPIs |
| Q2 2026 | 45 / 100 | **▼ 41 pts** | 4 promises withdrawn, 2 KPIs dark, hedging +34%, contradicted by layoffs + downgrade |

> *"Two commitments withdrawn, two KPIs dropped, hedging language up sharply, narrative contradicted by live signals."*

---

## Quick Start — offline, no API keys needed

```bash
# Clone
git clone https://github.com/suriya911/oddsmith-mispricing-detector.git
cd oddsmith-mispricing-detector

# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env          # fill in keys when ready; works blank in offline mode
uvicorn main:app --reload     # → http://localhost:8000/docs

# Frontend (separate terminal)
cd ../frontend
npm install
cp .env.local.example .env.local
npm run dev                   # → http://localhost:3000
```

Open **http://localhost:3000**, type `NMBS`, click **Analyze**. Score drops 86 → 45 in seconds with full evidence trail, no API keys required.

---

## How It Works

### Analysis loop (`backend/agent.py`) — 9 steps

```
1  Recall prior quarter from Cognee knowledge graph (or local JSON)
2  Discover transcript sources via Bright Data SERP (or sample_data/)
3  Fetch transcript text via Bright Data Unlocker (or local files)
4  Summarize long sections with Featherless AI (or pass-through)
5  Score hedging density + extract promises/metrics via AI/ML API (or rule-based)
6  Diff: withdrawn firm promises · dropped metrics · hedge delta
7  Fetch live signals via Bright Data (news · jobs · filings · reviews)
8  Spin-vs-reality: check each optimistic claim against live signals (AI/ML API)
9  Compute deterministic credibility score · store quarter to Cognee · return report
```

### Credibility score — deterministic and auditable

```
score = 100
  − 14 × count(withdrawn_promises)     each commitment quietly dropped
  −  8 × count(dropped_metrics)         each KPI that went dark
  − 30 × max(0, hedge_delta)            tone deterioration (0–1 scale)
  − 12 × count(contradicted_claims)     confirmed by live signals ≥ 65% confidence
  clamped 0–100
```

Every point deducted maps to a direct quote and a source URL — judges can audit the math.

---

## UI — Bloomberg-terminal aesthetic

| Panel | What it shows |
|-------|--------------|
| **Score gauge** | 0–100 arc with point-by-point deduction breakdown |
| **Transcript viewer** | Full text with hedging phrases highlighted in red; QoQ density badge; Q1/Q2 toggle |
| **Vanished promises** | Q1 firm commitment vs Q2 walk-back, side by side |
| **Spin vs Reality** | Management claim (left) · contradicting live signal + source link (right) |
| **Activity stream** | Live SSE feed of the 9-step agent loop as it runs |
| **Graph Q&A** | Ask Cognee anything — *"What did NMBS stop disclosing?"* |

---

## Project Layout

```
.github/
  workflows/
    ci.yml           lint · typecheck · pytest · Next.js build (every push/PR)
    deploy.yml       Render deploy hook + Vercel CLI (on merge to main)
backend/
  agent.py           9-step analysis orchestrator
  scoring.py         Hedging density + promise/metric extraction; AI/ML API + rule-based fallback
  memory.py          Cognee store/recall; local JSON fallback
  brightdata.py      Transcript discovery + live signal fetching; sample_data/ fallback
  main.py            FastAPI: POST /analyze · GET /report · GET /transcript · GET /activity · GET /graph/search
  models.py          Pydantic schemas (CredibilityReport, Finding, QuarterData, …)
  test_engine.py     31 pytest tests — all offline, run in 0.4 s
  requirements.txt
  .env.example
frontend/
  app/               Next.js 14 App Router
  components/        ScoreGauge · TranscriptViewer · VanishedPromises · SpinReality · ActivityStream · GraphSearch
  lib/api.ts         Typed API client
sample_data/
  NMBS_Q1_2026_transcript.txt
  NMBS_Q2_2026_transcript.txt
  live_signals.csv
  GROUND_TRUTH_annotations.txt
render.yaml          Render deploy config (backend)
frontend/vercel.json Vercel deploy config (frontend)
HOW_TO_GET_API_KEYS.md
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/analyze` | Start analysis job → returns `{job_id}` |
| `GET` | `/jobs/{job_id}` | Poll job status + full report on completion |
| `GET` | `/report/{company}` | Last stored report for a ticker |
| `GET` | `/transcript/{company}/{quarter}` | Raw text + hedging spans for the viewer |
| `GET` | `/activity/{job_id}` | SSE stream of live agent steps |
| `GET` | `/graph/search?q=…` | Free-form Cognee knowledge-graph query |
| `GET` | `/health` | Liveness check |

Interactive docs at **http://localhost:8000/docs**.

---

## API Keys

The app runs fully offline without any keys — rule-based scoring + `sample_data/`. Add keys to `backend/.env` before going live.

See **[HOW_TO_GET_API_KEYS.md](HOW_TO_GET_API_KEYS.md)** for step-by-step instructions.

| Service | Purpose | Promo code |
|---------|---------|-----------|
| [AI/ML API](https://aimlapi.com) | Hedging scoring + spin-vs-reality checks | — |
| [Featherless AI](https://featherless.ai) | Cheap bulk transcript summarization | `WEBDATA26` |
| [Cognee](https://cognee.ai) | Knowledge-graph memory for cross-quarter diffs | `WEBDATA26` |
| [Bright Data](https://brightdata.com) | Live transcript + signal scraping past bot-walls | `unlocked` |

---

## CI / CD

| Workflow | Trigger | Steps |
|----------|---------|-------|
| **CI** | every push + PR | `ruff` lint → FastAPI import check → `pytest` (31 tests) → `tsc` → `next build` |
| **Deploy** | merge to `main` | Render deploy hook (backend) + Vercel CLI (frontend) |

### Secrets required for deploy

Add in **GitHub → Settings → Secrets and variables → Actions**:

| Secret | Where to get it |
|--------|----------------|
| `RENDER_DEPLOY_HOOK_URL` | Render dashboard → service → Settings → Deploy hooks |
| `VERCEL_TOKEN` | vercel.com/account/tokens |
| `VERCEL_ORG_ID` | Vercel → Settings → General → Team ID |
| `VERCEL_PROJECT_ID` | Vercel project → Settings → General |

> Vercel also auto-deploys when you link the repo at vercel.com — the workflow is a redundant trigger.

---

## Testing

```bash
cd backend
pytest test_engine.py -v
# 31 passed in 0.37s — fully offline, no API keys needed
```

Test coverage: Q1/Q2 scoring · hedging detection · promise extraction · cross-quarter diff · live signal loading · spin-vs-reality · credibility score arithmetic · full agent integration.

---

## Deploy

**Backend → Render**

`render.yaml` is in the repo root. Connect the repo in the Render dashboard, add the four API key env vars, and deploy. The service runs `uvicorn main:app --host 0.0.0.0 --port $PORT`.

**Frontend → Vercel**

Set the root directory to `frontend/` and add one env var:
```
NEXT_PUBLIC_API_URL = https://your-render-service.onrender.com
```

---

## Team

**SignalForge** — Suriya + Sabari

Built for the [lablab.ai](https://lablab.ai) hackathon using Bright Data · Cognee · AI/ML API · Featherless AI.

*Research and analyst augmentation only. Not financial advice.*
