"""
Hedging-density scoring and promise/metric extraction.
Uses AI/ML API (OpenAI-compatible) when AIML_API_KEY is set;
falls back to a rule-based engine for offline demos.
"""
from __future__ import annotations
import os, re, json, logging
from typing import Any

from models import QuarterData, Promise, Metric, SpinCheck, LiveSignal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hedging word list (rule-based fallback)
# ---------------------------------------------------------------------------
_HEDGING_PHRASES: list[str] = [
    "we believe", "we think", "we feel", "we expect", "we hope",
    "challenging", "dynamic", "uncertain", "uncertainty", "prudent",
    "thoughtfully", "thoughtful", "evaluate", "evaluating",
    "over time", "measured", "selective", "as plans firm up",
    "prioritize", "may", "might", "could", "levers within our control",
    "we remain focused", "anchoring to", "near-term timeframe",
    "optimal phasing", "more as plans", "continue to evaluate",
    "we are focused on", "quality rather than", "measured view",
    "in the current environment", "macro uncertainty",
]

_CONFIDENT_PHRASES: list[str] = [
    "firm target", "clear path", "very confident", "i want to be direct",
    "on track", "as planned", "committed to", "we are committed",
    "reaffirming", "exceptional", "strong", "well ahead",
]


def _rule_based_hedging_density(text: str) -> tuple[float, list[str]]:
    text_lower = text.lower()
    sentences = re.split(r"[.!?]", text_lower)
    total = max(len([s for s in sentences if s.strip()]), 1)

    hedged_sentences: set[int] = set()
    found_markers: list[str] = []

    for phrase in _HEDGING_PHRASES:
        for i, sent in enumerate(sentences):
            if phrase in sent:
                hedged_sentences.add(i)
                if phrase not in found_markers:
                    found_markers.append(phrase)

    density = round(len(hedged_sentences) / total, 3)
    return density, found_markers


def _rule_based_tone(density: float) -> str:
    if density < 0.15:
        return "confident"
    if density < 0.30:
        return "neutral"
    return "hedged"


def _extract_management_text(text: str) -> str:
    """Return only CEO/CFO/management speech lines, stripping analyst questions."""
    lines = text.splitlines()
    mgmt_lines: list[str] = []
    in_mgmt = False
    mgmt_speakers = {"maria chen", "david okafor", "ceo", "cfo", "operator"}
    analyst_speakers = {"sarah lin", "tom reyes", "analyst"}

    for line in lines:
        line_lower = line.lower().strip()
        if any(f"({role})" in line_lower or line_lower.startswith(role) for role in mgmt_speakers):
            in_mgmt = True
        elif any(f"({role})" in line_lower or line_lower.startswith(role) for role in analyst_speakers):
            in_mgmt = False
        elif line_lower.startswith("operator"):
            in_mgmt = False

        if in_mgmt:
            mgmt_lines.append(line)

    return " ".join(mgmt_lines) if mgmt_lines else text


def _rule_based_promises(text: str) -> list[Promise]:
    promises: list[Promise] = []
    # Only extract from management sections to avoid analyst questions
    mgmt_text = _extract_management_text(text).lower()

    firm_patterns = [
        (r"firm target[^.?]+\.", "firm"),
        (r"committed to[^.?]+(?:q[1-4]|profitab|operational|revenue)[^.?]*\.", "firm"),
        (r"on track[^.?]+\.", "firm"),
        (r"as planned[^.?]+\.", "firm"),
        (r"fully operational[^.?]+\.", "firm"),
        (r"profitability by q[1-4]\s*\d{4}[^.?]*\.", "firm"),
        (r"guiding to[^.?]+\.", "firm"),
        (r"reaffirm[^.?]+\.", "firm"),
        (r"hub[^.?]+(?:q3|operational)[^.?]*\.", "firm"),
        (r"clear path[^.?]+\.", "firm"),
    ]
    soft_patterns = [
        (r"we believe[^.?]+\.", "soft"),
        (r"we think[^.?]+\.", "soft"),
        (r"we are focused on[^.?]+\.", "soft"),
        (r"confident in[^.?]+opportunity[^.?]*\.", "soft"),
        (r"investing thoughtfully[^.?]+\.", "soft"),
        (r"path to profitability[^.?]+\.", "soft"),
        (r"resilient[^.?]+franchise[^.?]*\.", "soft"),
        (r"fundamentals[^.?]+solid[^.?]*\.", "soft"),
    ]

    seen_topic_keys: set[str] = set()
    for pattern, specificity in firm_patterns + soft_patterns:
        for m in re.finditer(pattern, mgmt_text):
            snippet = m.group(0).strip()
            # Skip walk-back language that looks like a promise but isn't
            if any(w in snippet for w in ["rather than anchoring", "optimal phasing", "plans firm up", "continue to evaluate", "quality rather than"]):
                continue
            if len(snippet) < 15:
                continue
            # Deduplicate semantically: group promises by their core topic
            topic_key = _promise_topic_key(snippet)
            if topic_key in seen_topic_keys:
                continue
            seen_topic_keys.add(topic_key)
            metric_or_date = ""
            date_m = re.search(r"q[1-4]\s*\d{4}|end of q[1-4]|q4\s*\d{4}", snippet)
            if date_m:
                metric_or_date = date_m.group(0)
            num_m = re.search(r"\$[\d,.]+[bm]?|\d+%", snippet)
            if num_m and not metric_or_date:
                metric_or_date = num_m.group(0)
            promises.append(Promise(
                text=snippet[:200],
                specificity=specificity,
                metric_or_date=metric_or_date,
            ))
    return promises


def _promise_topic_key(text: str) -> str:
    """Derive a coarse topic key so near-duplicate promises are merged."""
    t = text.lower()
    if any(w in t for w in ["profitab", "ebitda", "q4", "breakeven"]):
        return "profitability_q4"
    if any(w in t for w in ["hub", "west coast", "q3", "operational", "capacity"]):
        return "westcoast_hub_q3"
    if any(w in t for w in ["revenue", "guidance", "guiding", "$2"]):
        return "revenue_guidance"
    if any(w in t for w in ["resilient", "franchise", "fundamental"]):
        return "resilience_claim"
    if any(w in t for w in ["path to profitability", "path to"]):
        return "path_to_profitability"
    # Fallback: first 40 chars
    return re.sub(r"\s+", "_", t[:40])


def _rule_based_metrics(text: str) -> list[Metric]:
    metrics: list[Metric] = []
    patterns = [
        (r"revenue[^,\n]{0,30}?\$[\d,.]+\s*(?:million|billion)?", "revenue"),
        (r"gross margin[^,\n]{0,30}?[\d.]+%", "gross_margin"),
        (r"enterprise customer count[^,\n]{0,60}", "enterprise_customer_count"),
        # net revenue retention: can be "stands at a healthy 118%" or "at 118%"
        (r"net revenue retention[^,\n.]{0,60}", "net_revenue_retention"),
        (r"retention[^,\n]{0,20}?[\d.]+%", "net_revenue_retention"),
        (r"cash[^,\n]{0,40}?\$[\d,.]+\s*(?:million|billion)?", "cash"),
        (r"(?:up|grew|growth)[^,\n]{0,20}?\d+%", "growth_rate"),
        (r"(?:reached|at)\s*[\d,]+,?\s*up\s*\d+%", "customer_count"),
        (r"1[,.]2\d+[^,\n]{0,30}up \d+%", "customer_count"),
    ]
    seen: set[str] = set()
    text_lower = text.lower()
    for pattern, name in patterns:
        for m in re.finditer(pattern, text_lower):
            val = m.group(0).strip()
            # Dedupe by name — keep the most specific (longest) match
            existing = next((x for x in metrics if x.name == name), None)
            if existing is None:
                metrics.append(Metric(name=name, value=val[:120]))
                seen.add(val)
            elif len(val) > len(existing.value) and val not in seen:
                existing.value = val[:120]
                seen.add(val)
    return metrics


# ---------------------------------------------------------------------------
# AI/ML API path
# ---------------------------------------------------------------------------
def _get_aiml_client():
    from openai import OpenAI
    return OpenAI(
        api_key=os.environ["AIML_API_KEY"],
        base_url="https://api.aimlapi.com/v1",
    )


_SCORE_SYSTEM = """You are an equity-research language analyst. Given an earnings-call transcript, return ONLY valid JSON with no prose, no markdown:
{
  "hedging_density": <0-1>,
  "hedging_markers": ["..."],
  "tone": "confident|neutral|hedged",
  "promises": [{"text": "...", "specificity": "firm|soft", "metric_or_date": "..."}],
  "disclosed_metrics": [{"name": "...", "value": "..."}]
}"""

_SPIN_SYSTEM = """You are an equity-research fact-checker. Given a management claim and a live market signal, return ONLY valid JSON:
{"contradicts": true|false, "explanation": "...", "confidence": 0-1}"""


def _llm_score(transcript: str) -> dict[str, Any]:
    client = _get_aiml_client()
    resp = client.chat.completions.create(
        model=os.getenv("AIML_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": _SCORE_SYSTEM},
            {"role": "user", "content": f"Transcript:\n\n{transcript[:12000]}"},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


def _llm_spin_check(claim: str, signal_headline: str, signal_detail: str) -> dict[str, Any]:
    client = _get_aiml_client()
    resp = client.chat.completions.create(
        model=os.getenv("AIML_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": _SPIN_SYSTEM},
            {"role": "user", "content": (
                f"Management claim: {claim}\n\n"
                f"Live signal — {signal_headline}: {signal_detail}"
            )},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


# ---------------------------------------------------------------------------
# Featherless summarisation (cheap condense before scoring)
# ---------------------------------------------------------------------------
def _get_featherless_client():
    from openai import OpenAI
    return OpenAI(
        api_key=os.environ["FEATHERLESS_API_KEY"],
        base_url="https://api.featherless.ai/v1",
    )


def summarize_for_scoring(transcript: str) -> str:
    if not os.getenv("FEATHERLESS_API_KEY"):
        return transcript  # pass-through in offline mode
    try:
        client = _get_featherless_client()
        resp = client.chat.completions.create(
            model=os.getenv("FEATHERLESS_MODEL", "mistralai/Mistral-7B-Instruct-v0.2"),
            messages=[
                {"role": "system", "content": (
                    "Condense this earnings call transcript to key statements: "
                    "metrics disclosed, forward commitments, tone. "
                    "Preserve all specific numbers, dates, and direct quotes. "
                    "Max 800 words."
                )},
                {"role": "user", "content": transcript[:15000]},
            ],
            temperature=0,
            max_tokens=900,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.warning(f"Featherless summarization failed, using raw transcript: {e}")
        return transcript


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def score_transcript(transcript: str, company: str, quarter: str) -> QuarterData:
    """Score a transcript; uses AI/ML API if key is set, else rule-based."""
    condensed = summarize_for_scoring(transcript)

    if os.getenv("AIML_API_KEY"):
        try:
            raw = _llm_score(condensed)
            return QuarterData(
                company=company,
                quarter=quarter,
                hedging_density=float(raw.get("hedging_density", 0)),
                hedging_markers=raw.get("hedging_markers", []),
                tone=raw.get("tone", "neutral"),
                promises=[Promise(**p) for p in raw.get("promises", [])],
                disclosed_metrics=[Metric(**m) for m in raw.get("disclosed_metrics", [])],
                raw_transcript=transcript,
            )
        except Exception as e:
            logger.warning(f"AI/ML API scoring failed, falling back to rule-based: {e}")

    density, markers = _rule_based_hedging_density(condensed)
    return QuarterData(
        company=company,
        quarter=quarter,
        hedging_density=density,
        hedging_markers=markers,
        tone=_rule_based_tone(density),
        promises=_rule_based_promises(condensed),
        disclosed_metrics=_rule_based_metrics(condensed),
        raw_transcript=transcript,
    )


def check_spin_vs_reality(claims: list[Promise], signals: list[LiveSignal]) -> list[SpinCheck]:
    """Check each claim against live signals; AI/ML API if available, else heuristic."""
    results: list[SpinCheck] = []

    # Heuristic keyword matching for offline mode
    def _heuristic_check(claim_text: str, signal: LiveSignal) -> tuple[bool, float]:
        contradiction_keywords = ["layoff", "cut", "downgrade", "cancel", "decline",
                                   "fall", "drop", "exit", "departure", "down", "terminate"]
        signal_combined = (signal.headline + " " + signal.detail).lower()
        claim_lower = claim_text.lower()
        positive_claim = any(w in claim_lower for w in [
            "resilient", "confident", "investing", "strong", "growth",
            "strategic", "quality", "solid", "fundamentals"
        ])
        negative_signal = any(w in signal_combined for w in contradiction_keywords)
        if positive_claim and negative_signal:
            return True, 0.8
        return False, 0.2

    for signal in signals:
        best_claim: Promise | None = None
        best_contradicts = False
        best_confidence = 0.0
        best_explanation = ""

        for promise in claims:
            if os.getenv("AIML_API_KEY"):
                try:
                    raw = _llm_spin_check(promise.text, signal.headline, signal.detail)
                    contradicts = raw.get("contradicts", False)
                    confidence = float(raw.get("confidence", 0))
                    if contradicts and confidence > best_confidence:
                        best_confidence = confidence
                        best_contradicts = True
                        best_claim = promise
                        best_explanation = raw.get("explanation", "")
                    continue
                except Exception as e:
                    logger.warning(f"AI/ML spin check failed: {e}")

            contradicts, confidence = _heuristic_check(promise.text, signal)
            if contradicts and confidence > best_confidence:
                best_confidence = confidence
                best_contradicts = True
                best_claim = promise
                best_explanation = f"Signal '{signal.headline}' contradicts management's claim about '{promise.text[:60]}'"

        # Fallback: if no claim matched but signal clearly contradicts general optimism
        if best_claim is None and claims:
            contradicts, confidence = _heuristic_check(claims[0].text, signal)
            if contradicts:
                best_claim = claims[0]
                best_contradicts = True
                best_confidence = confidence
                best_explanation = f"'{signal.headline}' contradicts management's optimistic tone."

        if best_claim is not None:
            results.append(SpinCheck(
                claim=best_claim.text,
                contradicts=best_contradicts,
                explanation=best_explanation,
                confidence=best_confidence,
                signal=signal,
            ))

    return results
