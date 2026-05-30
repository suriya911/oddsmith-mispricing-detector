# VerbaTrust — Management Credibility Engine

> *"Management always sounds confident. Our engine reads what they stopped saying."*

VerbaTrust scores management credibility by diffing earnings-call language against prior quarters (via Cognee knowledge graph) and cross-checking the optimistic narrative against live web signals (via Bright Data).

**Output:** A Credibility Score (0–100) with every finding linked to an evidence quote and a source URL.

---

## Demo

Default demo company: **NMBS** (Nimbus Logistics — fictional, copyright-clean).

| Quarter | Score | Change |
|---------|-------|--------|
| Q1 2026 | 86/100 | — |
| Q2 2026 | 45/100 | **▼ 41 pts** |

NMBS Q2 findings: 4 commitments withdrawn · 2 KPIs went dark · hedging up +34% · narrative contradicted by layoffs + downgrade.

---

## Quick Start (offline, no API keys needed)

```bash
# 1. Backend
cd backend
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload

# 2. Frontend
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open **http://localhost:3000**, enter `NMBS`, click **Analyze**.

---

## Architecture

```
frontend/          Next.js 14 — Bloomberg-terminal UI
backend/
  main.py          FastAPI endpoints
  agent.py         9-step analysis loop
  scoring.py       Hedging density + promise/metric extraction (AI/ML API + rule-based fallback)
  memory.py        Cognee graph store/recall (local JSON fallback)
  brightdata.py    Transcript + signal fetching (sample_data/ fallback)
  models.py        Pydantic schemas
  requirements.txt
  .env.example
sample_data/       NMBS demo transcripts + live_signals.csv
```

### Analysis Loop (agent.py)

```
1. Recall prior quarter (Cognee / local JSON)
2. Discover transcript sources (Bright Data SERP / local files)
3. Fetch transcript text (Bright Data Unlocker / local files)
4. Summarize with Featherless (or pass-through)
5. Score hedging + extract promises/metrics (AI/ML API / rule-based)
6. Compute diff: withdrawn promises, dropped metrics, hedge delta
7. Fetch live signals (Bright Data / live_signals.csv)
8. Check spin-vs-reality (AI/ML API / heuristic)
9. Compute deterministic credibility score + store to memory
```

### Credibility Score (deterministic)

```
score = 100
 - 14 × withdrawn_promises   (each commitment quietly dropped)
 -  8 × dropped_metrics       (each KPI that went dark)
 - 30 × max(0, hedge_delta)   (tone deterioration, 0-1)
 - 12 × contradicted_claims   (confirmed by live signals)
 clamped 0–100
```

---

## API Keys

See **HOW_TO_GET_API_KEYS.md** for step-by-step instructions.

| Service | Purpose | Promo |
|---------|---------|-------|
| [AI/ML API](https://aimlapi.com) | Hedging scoring + spin checks | — |
| [Featherless AI](https://featherless.ai) | Cheap bulk summarization | `WEBDATA26` |
| [Cognee](https://cognee.ai) | Knowledge-graph memory | `WEBDATA26` |
| [Bright Data](https://brightdata.com) | Live transcript + signal scraping | `unlocked` |

The app runs fully offline without any keys set (uses `sample_data/` + rule-based scoring).

---

## Deploy

- **Backend → Render:** `render.yaml` in repo root. Set env vars in dashboard.
- **Frontend → Vercel:** set root directory to `frontend/`, add `NEXT_PUBLIC_API_URL` env var pointing to your Render URL.

---

## Team

SignalForge: Suriya + Sabari — built for lablab.ai hackathon.

*Research/analyst augmentation only — not financial advice.*
