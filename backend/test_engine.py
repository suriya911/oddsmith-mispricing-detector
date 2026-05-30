"""
Unit tests for the VerbaTrust scoring engine.
Run: pytest test_engine.py -v
All tests run fully offline — no API keys required.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import pytest
from pathlib import Path

SAMPLE = Path(__file__).parent.parent / "sample_data"

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def q1_text():
    return (SAMPLE / "NMBS_Q1_2026_transcript.txt").read_text(encoding="utf-8")

@pytest.fixture(scope="module")
def q2_text():
    return (SAMPLE / "NMBS_Q2_2026_transcript.txt").read_text(encoding="utf-8")

@pytest.fixture(scope="module")
def q1(q1_text):
    from scoring import score_transcript
    return score_transcript(q1_text, "NMBS", "Q1_2026")

@pytest.fixture(scope="module")
def q2(q2_text):
    from scoring import score_transcript
    return score_transcript(q2_text, "NMBS", "Q2_2026")

@pytest.fixture(scope="module")
def diff(q1, q2):
    from agent import _compute_diff
    return _compute_diff(q1, q2)

@pytest.fixture(scope="module")
def signals():
    from brightdata import fetch_live_signals
    return fetch_live_signals("NMBS")


# ── Scoring tests ─────────────────────────────────────────────────────────────

class TestQ1Scoring:
    def test_low_hedging_density(self, q1):
        assert q1.hedging_density < 0.15, f"Q1 should be low hedging, got {q1.hedging_density}"

    def test_confident_tone(self, q1):
        assert q1.tone == "confident"

    def test_has_firm_promises(self, q1):
        firm = [p for p in q1.promises if p.specificity == "firm"]
        assert len(firm) >= 2, "Q1 should have at least 2 firm promises"

    def test_profitability_promise_detected(self, q1):
        texts = " ".join(p.text.lower() for p in q1.promises)
        assert "profitab" in texts or "ebitda" in texts, "Q4 profitability promise should be detected"

    def test_hub_promise_detected(self, q1):
        texts = " ".join(p.text.lower() for p in q1.promises)
        assert "hub" in texts or "operational" in texts or "q3" in texts

    def test_metrics_extracted(self, q1):
        assert len(q1.disclosed_metrics) >= 3, "Q1 should disclose multiple metrics"

    def test_revenue_metric(self, q1):
        names = [m.name for m in q1.disclosed_metrics]
        assert "revenue" in names


class TestQ2Scoring:
    def test_high_hedging_density(self, q2):
        assert q2.hedging_density >= 0.3, f"Q2 should be high hedging, got {q2.hedging_density}"

    def test_hedged_tone(self, q2):
        assert q2.tone == "hedged"

    def test_no_firm_promises(self, q2):
        firm = [p for p in q2.promises if p.specificity == "firm"]
        assert len(firm) == 0, "Q2 should have 0 firm promises after walk-backs"

    def test_hedging_markers_include_expected(self, q2):
        combined = " ".join(q2.hedging_markers).lower()
        assert "we believe" in combined or "challenging" in combined or "prudent" in combined

    def test_fewer_metrics_than_q1(self, q1, q2):
        assert len(q2.disclosed_metrics) <= len(q1.disclosed_metrics)


# ── Diff / cross-quarter tests ────────────────────────────────────────────────

class TestDiff:
    def test_withdrawn_promises_detected(self, diff):
        assert len(diff.withdrawn_promises) >= 2, (
            f"Expected ≥2 withdrawn promises, got {len(diff.withdrawn_promises)}"
        )

    def test_dropped_metrics_detected(self, diff):
        assert len(diff.dropped_metrics) >= 1, (
            f"Expected ≥1 dropped metric, got {len(diff.dropped_metrics)}"
        )

    def test_hedge_delta_positive(self, diff):
        assert diff.hedge_delta > 0.1, (
            f"Hedge delta should be positive (Q2 more hedged), got {diff.hedge_delta}"
        )

    def test_hedge_delta_magnitude(self, diff):
        assert diff.hedge_delta >= 0.2, "Hedge delta should be substantial (>0.2)"


# ── Live signals tests ────────────────────────────────────────────────────────

class TestLiveSignals:
    def test_signals_loaded(self, signals):
        assert len(signals) >= 3, "Should load at least 3 live signals from sample CSV"

    def test_signal_fields_populated(self, signals):
        for s in signals:
            assert s.headline, "Signal headline should not be empty"
            assert s.source_type in ("news", "jobs", "filing", "reviews")

    def test_layoff_signal_present(self, signals):
        headlines = [s.headline.lower() for s in signals]
        assert any("layoff" in h or "cuts" in h or "workforce" in h for h in headlines)

    def test_downgrade_signal_present(self, signals):
        headlines = [s.headline.lower() for s in signals]
        assert any("downgrade" in h or "hold" in h for h in headlines)


# ── Spin-vs-reality tests ─────────────────────────────────────────────────────

class TestSpinVsReality:
    def test_contradictions_detected(self, q2, signals):
        from scoring import check_spin_vs_reality
        spin = check_spin_vs_reality(q2.promises, signals)
        contradictions = [s for s in spin if s.contradicts]
        assert len(contradictions) >= 2, (
            f"Expected ≥2 contradictions, got {len(contradictions)}"
        )

    def test_one_check_per_signal(self, q2, signals):
        from scoring import check_spin_vs_reality
        spin = check_spin_vs_reality(q2.promises, signals)
        # No more results than signals
        assert len(spin) <= len(signals), "Should be at most one check per signal"


# ── Credibility score tests ───────────────────────────────────────────────────

class TestCredibilityScore:
    def test_q1_baseline_score_reasonable(self, q1):
        from agent import _compute_diff, _compute_score
        d = _compute_diff(None, q1)
        score, _ = _compute_score(None, q1, d)
        assert 75 <= score <= 100, f"Q1 baseline score should be 75-100, got {score}"

    def test_q2_score_lower_than_q1(self, q1, q2, diff, signals):
        from agent import _compute_diff, _compute_score
        from scoring import check_spin_vs_reality
        diff.spin_checks = check_spin_vs_reality(q2.promises, signals)

        score_q2, _ = _compute_score(q1, q2, diff)
        d1 = _compute_diff(None, q1)
        score_q1, _ = _compute_score(None, q1, d1)

        assert score_q2 < score_q1, (
            f"Q2 score ({score_q2}) should be lower than Q1 ({score_q1})"
        )

    def test_q2_score_in_target_range(self, q1, q2, diff, signals):
        from agent import _compute_diff, _compute_score
        from scoring import check_spin_vs_reality
        diff.spin_checks = check_spin_vs_reality(q2.promises, signals)
        score, _ = _compute_score(q1, q2, diff)
        assert 30 <= score <= 60, f"Q2 score should land 30-60 (ground truth ~46), got {score}"

    def test_score_breakdown_sums_correctly(self, q1, q2, diff, signals):
        from agent import _compute_diff, _compute_score
        from scoring import check_spin_vs_reality
        diff.spin_checks = check_spin_vs_reality(q2.promises, signals)
        score, breakdown = _compute_score(q1, q2, diff)
        total_deducted = sum(breakdown.values())
        assert abs((100 - total_deducted) - score) < 0.1, (
            "Score should equal 100 minus sum of deductions"
        )

    def test_score_clamped_0_to_100(self, q1, q2, diff, signals):
        from agent import _compute_diff, _compute_score
        from scoring import check_spin_vs_reality
        diff.spin_checks = check_spin_vs_reality(q2.promises, signals)
        score, _ = _compute_score(q1, q2, diff)
        assert 0 <= score <= 100


# ── Full agent integration test ───────────────────────────────────────────────

class TestAgentIntegration:
    def test_full_analyze_returns_report(self):
        from agent import analyze
        report = analyze("NMBS", mode="offline")
        assert report.company == "NMBS"
        assert report.score is not None
        assert 0 <= report.score <= 100
        assert len(report.findings) >= 3

    def test_report_has_summary(self):
        from agent import analyze
        report = analyze("NMBS", mode="offline")
        assert len(report.summary) > 20

    def test_prior_score_higher(self):
        from agent import analyze
        report = analyze("NMBS", mode="offline")
        if report.prior_score is not None:
            assert report.score < report.prior_score, (
                "Q2 credibility should be lower than Q1"
            )

    def test_activity_log_populated(self):
        from agent import analyze, get_activity_log
        analyze("NMBS", mode="offline")
        log = get_activity_log()
        assert len(log) >= 9, "Activity log should have ≥9 steps"
        assert any("[1/9]" in line for line in log)
        assert any("[9/9]" in line for line in log)
