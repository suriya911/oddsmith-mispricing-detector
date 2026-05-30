from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal


class Promise(BaseModel):
    text: str
    specificity: Literal["firm", "soft"]
    metric_or_date: str = ""


class Metric(BaseModel):
    name: str
    value: str


class QuarterData(BaseModel):
    company: str
    quarter: str  # e.g. "Q1_2026"
    hedging_density: float = Field(ge=0, le=1)
    hedging_markers: list[str] = []
    tone: Literal["confident", "neutral", "hedged"]
    promises: list[Promise] = []
    disclosed_metrics: list[Metric] = []
    raw_transcript: str = ""


class LiveSignal(BaseModel):
    date: str
    source_type: str
    headline: str
    detail: str
    contradicts_claim: str
    source_url: str


class Finding(BaseModel):
    category: Literal[
        "withdrawn_promise",
        "dropped_metric",
        "hedge_increase",
        "spin_vs_reality",
    ]
    description: str
    evidence_quote: str
    source_url: str = ""
    points_deducted: float


class SpinCheck(BaseModel):
    claim: str
    contradicts: bool
    explanation: str
    confidence: float = Field(ge=0, le=1)
    signal: LiveSignal


class DiffResult(BaseModel):
    withdrawn_promises: list[Promise] = []
    dropped_metrics: list[Metric] = []
    hedge_delta: float = 0.0
    spin_checks: list[SpinCheck] = []


class CredibilityReport(BaseModel):
    company: str
    current_quarter: str
    prior_quarter: str | None = None
    score: float = Field(ge=0, le=100)
    prior_score: float | None = None
    score_delta: float | None = None
    tone: str
    hedging_density: float
    prior_hedging_density: float | None = None
    findings: list[Finding] = []
    score_breakdown: dict[str, float] = {}
    summary: str = ""
    current_quarter_data: QuarterData | None = None
    prior_quarter_data: QuarterData | None = None


class AnalyzeRequest(BaseModel):
    company: str
    mode: Literal["offline", "live"] = "offline"
