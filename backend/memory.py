"""
Cognee knowledge-graph wrappers for cross-quarter memory.
Uses Cognee when COGNEE_API_KEY is set; falls back to a local JSON store.
"""
from __future__ import annotations
import os, json, logging
from pathlib import Path

from models import QuarterData

logger = logging.getLogger(__name__)

_LOCAL_STORE = Path(__file__).parent.parent / "cognee_data" / "quarters.json"


# ---------------------------------------------------------------------------
# Local JSON fallback
# ---------------------------------------------------------------------------
def _load_local() -> dict:
    if _LOCAL_STORE.exists():
        return json.loads(_LOCAL_STORE.read_text(encoding="utf-8"))
    return {}


def _save_local(data: dict) -> None:
    _LOCAL_STORE.parent.mkdir(parents=True, exist_ok=True)
    _LOCAL_STORE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Cognee path
# ---------------------------------------------------------------------------
def _cognee_store(quarter_data: QuarterData) -> None:
    import cognee
    text = (
        f"Company: {quarter_data.company}\n"
        f"Quarter: {quarter_data.quarter}\n"
        f"Hedging density: {quarter_data.hedging_density}\n"
        f"Tone: {quarter_data.tone}\n"
        f"Promises: {json.dumps([p.model_dump() for p in quarter_data.promises])}\n"
        f"Metrics: {json.dumps([m.model_dump() for m in quarter_data.disclosed_metrics])}\n"
        f"Hedging markers: {', '.join(quarter_data.hedging_markers)}"
    )
    import asyncio
    asyncio.run(_cognee_store_async(text, quarter_data))


async def _cognee_store_async(text: str, quarter_data: QuarterData) -> None:
    import cognee
    await cognee.add(text, dataset_name=f"{quarter_data.company}_{quarter_data.quarter}")
    await cognee.cognify()


def _cognee_recall(company: str) -> QuarterData | None:
    import asyncio
    return asyncio.run(_cognee_recall_async(company))


async def _cognee_recall_async(company: str) -> QuarterData | None:
    import cognee
    results = await cognee.search(f"promises and metrics for {company} prior quarter")
    if not results:
        return None
    # Cognee returns text chunks; we try to parse the most recent one
    for chunk in results:
        text = getattr(chunk, "text", str(chunk))
        if company.lower() in text.lower():
            try:
                return _parse_cognee_text(text, company)
            except Exception:
                continue
    return None


def _parse_cognee_text(text: str, company: str) -> QuarterData:
    import re
    quarter = re.search(r"Quarter:\s*(\S+)", text)
    hedging = re.search(r"Hedging density:\s*([\d.]+)", text)
    tone_m = re.search(r"Tone:\s*(\w+)", text)
    promises_m = re.search(r"Promises:\s*(\[.*?\])", text, re.DOTALL)
    metrics_m = re.search(r"Metrics:\s*(\[.*?\])", text, re.DOTALL)
    markers_m = re.search(r"Hedging markers:\s*(.+)", text)

    from models import Promise, Metric
    promises = json.loads(promises_m.group(1)) if promises_m else []
    metrics = json.loads(metrics_m.group(1)) if metrics_m else []

    return QuarterData(
        company=company,
        quarter=quarter.group(1) if quarter else "unknown",
        hedging_density=float(hedging.group(1)) if hedging else 0.0,
        tone=tone_m.group(1) if tone_m else "neutral",
        promises=[Promise(**p) for p in promises],
        disclosed_metrics=[Metric(**m) for m in metrics],
        hedging_markers=markers_m.group(1).split(", ") if markers_m else [],
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def store(quarter_data: QuarterData) -> None:
    """Persist a quarter's scored data."""
    if os.getenv("COGNEE_API_KEY"):
        try:
            _cognee_store(quarter_data)
            logger.info(f"Stored {quarter_data.company} {quarter_data.quarter} in Cognee")
        except Exception as e:
            logger.warning(f"Cognee store failed, falling back to local: {e}")

    local = _load_local()
    key = f"{quarter_data.company}:{quarter_data.quarter}"
    local[key] = quarter_data.model_dump()
    _save_local(local)
    logger.info(f"Stored {quarter_data.company} {quarter_data.quarter} locally")


def recall(company: str) -> QuarterData | None:
    """Return the most recent prior quarter's data for a company."""
    if os.getenv("COGNEE_API_KEY"):
        try:
            result = _cognee_recall(company)
            if result:
                return result
        except Exception as e:
            logger.warning(f"Cognee recall failed, falling back to local: {e}")

    local = _load_local()
    company_entries = {
        k: v for k, v in local.items() if k.startswith(f"{company}:")
    }
    if not company_entries:
        return None

    # Sort by quarter key to get the most recent
    sorted_keys = sorted(company_entries.keys())
    latest_key = sorted_keys[-1]
    data = company_entries[latest_key]
    return QuarterData(**data)


def recall_all(company: str) -> list[QuarterData]:
    """Return all stored quarters for a company, oldest first."""
    local = _load_local()
    entries = [
        QuarterData(**v)
        for k, v in local.items()
        if k.startswith(f"{company}:")
    ]
    return sorted(entries, key=lambda q: q.quarter)


def search_graph(query: str) -> str:
    """Free-form graph query (live demo Q&A). Returns a text answer."""
    if not os.getenv("COGNEE_API_KEY"):
        return _local_search(query)
    try:
        import asyncio, cognee
        results = asyncio.run(cognee.search(query))
        texts = [getattr(r, "text", str(r)) for r in results[:3]]
        return "\n\n".join(texts) if texts else "No results found."
    except Exception as e:
        logger.warning(f"Cognee search failed: {e}")
        return _local_search(query)


def _local_search(query: str) -> str:
    local = _load_local()
    if not local:
        return "No data stored yet. Run /analyze first."
    query_lower = query.lower()
    matches: list[str] = []
    for key, data in local.items():
        entry_text = json.dumps(data).lower()
        if any(word in entry_text for word in query_lower.split()):
            company, quarter = key.split(":", 1)
            qd = QuarterData(**data)
            matches.append(
                f"{company} {quarter}: hedging_density={qd.hedging_density}, "
                f"tone={qd.tone}, promises={len(qd.promises)}, "
                f"metrics={len(qd.disclosed_metrics)}"
            )
    return "\n".join(matches) if matches else "No matching data found."
