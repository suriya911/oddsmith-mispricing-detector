"""
Bright Data integration for live transcript + signal fetching.
All calls fall back to sample_data/ when BRIGHTDATA_API_KEY is unset.
"""
from __future__ import annotations
import os, csv, logging
from pathlib import Path

import httpx

from models import LiveSignal

logger = logging.getLogger(__name__)

_SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"
_BD_BASE = "https://api.brightdata.com"


# ---------------------------------------------------------------------------
# Transcript discovery & fetching
# ---------------------------------------------------------------------------

def discover_transcripts(company: str) -> list[str]:
    """
    Return a list of transcript source URLs for a company.
    In offline mode returns local file paths (as strings) from sample_data/.
    In live mode uses Bright Data SERP to find Seeking Alpha / Motley Fool pages.
    """
    if not os.getenv("BRIGHTDATA_API_KEY"):
        files = sorted(_SAMPLE_DIR.glob(f"{company.upper()}_*_transcript.txt"))
        if not files:
            files = sorted(_SAMPLE_DIR.glob("NMBS_*_transcript.txt"))
        return [str(f) for f in files]

    query = f"{company} earnings call transcript site:seekingalpha.com OR site:fool.com"
    try:
        resp = httpx.post(
            f"{_BD_BASE}/serp",
            headers={"Authorization": f"Bearer {os.environ['BRIGHTDATA_API_KEY']}"},
            json={"query": query, "num": 5},
            timeout=30,
        )
        resp.raise_for_status()
        results = resp.json().get("organic", [])
        return [r["url"] for r in results]
    except Exception as e:
        logger.warning(f"Bright Data SERP failed, using sample files: {e}")
        return [str(f) for f in sorted(_SAMPLE_DIR.glob("NMBS_*_transcript.txt"))]


def fetch_transcript(source: str) -> str:
    """
    Fetch transcript text from a URL (Bright Data Unlocker) or local path.
    """
    if source.endswith(".txt") or Path(source).exists():
        return Path(source).read_text(encoding="utf-8")

    if not os.getenv("BRIGHTDATA_API_KEY"):
        return ""

    try:
        resp = httpx.post(
            f"{_BD_BASE}/unlocker",
            headers={"Authorization": f"Bearer {os.environ['BRIGHTDATA_API_KEY']}"},
            json={"url": source, "render_js": False},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("html", "")
    except Exception as e:
        logger.error(f"Bright Data Unlocker failed for {source}: {e}")
        return ""


# ---------------------------------------------------------------------------
# Live signals
# ---------------------------------------------------------------------------

def fetch_live_signals(company: str) -> list[LiveSignal]:
    """
    Return live web signals (news, jobs, filings, reviews) for a company.
    In offline mode reads from sample_data/live_signals.csv.
    In live mode scrapes via Bright Data.
    """
    if not os.getenv("BRIGHTDATA_API_KEY"):
        return _load_sample_signals(company)

    signals: list[LiveSignal] = []
    try:
        signals.extend(_fetch_news_signals(company))
    except Exception as e:
        logger.warning(f"Bright Data news fetch failed: {e}")

    try:
        signals.extend(_fetch_filing_signals(company))
    except Exception as e:
        logger.warning(f"Bright Data filings fetch failed: {e}")

    if not signals:
        logger.info("Live signals empty; falling back to sample data")
        return _load_sample_signals(company)

    return signals


def _load_sample_signals(company: str) -> list[LiveSignal]:
    csv_path = _SAMPLE_DIR / "live_signals.csv"
    if not csv_path.exists():
        return []
    signals: list[LiveSignal] = []
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            signals.append(LiveSignal(
                date=row.get("date", ""),
                source_type=row.get("source_type", ""),
                headline=row.get("headline", ""),
                detail=row.get("detail", ""),
                contradicts_claim=row.get("contradicts_claim", ""),
                source_url=row.get("source_url_placeholder", ""),
            ))
    return signals


def _fetch_news_signals(company: str) -> list[LiveSignal]:
    resp = httpx.get(
        f"{_BD_BASE}/datasets/v3/trigger",
        headers={"Authorization": f"Bearer {os.environ['BRIGHTDATA_API_KEY']}"},
        params={
            "dataset_id": "gd_lz11l67i0cbsf7alv5",  # news dataset
            "company": company,
            "type": "discover_new",
        },
        timeout=30,
    )
    resp.raise_for_status()
    items = resp.json().get("data", [])
    return [
        LiveSignal(
            date=item.get("date", ""),
            source_type="news",
            headline=item.get("title", ""),
            detail=item.get("description", ""),
            contradicts_claim="",
            source_url=item.get("url", ""),
        )
        for item in items
    ]


def _fetch_filing_signals(company: str) -> list[LiveSignal]:
    resp = httpx.get(
        f"{_BD_BASE}/datasets/v3/trigger",
        headers={"Authorization": f"Bearer {os.environ['BRIGHTDATA_API_KEY']}"},
        params={
            "dataset_id": "gd_sec_filings",
            "ticker": company.upper(),
            "type": "discover_new",
        },
        timeout=30,
    )
    resp.raise_for_status()
    items = resp.json().get("data", [])
    return [
        LiveSignal(
            date=item.get("filed_at", ""),
            source_type="filing",
            headline=item.get("form_type", "") + " — " + item.get("description", ""),
            detail=item.get("summary", ""),
            contradicts_claim="",
            source_url=item.get("url", ""),
        )
        for item in items
    ]
