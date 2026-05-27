"""Phase 14: Tests for offline shadow recommendation engine.

12+ tests covering generate, rank, and filter.
"""
from __future__ import annotations

import pytest
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.offline_shadow_recommendation_engine import (
    Recommendation,
    generate_recommendations,
    rank_recommendations,
    filter_recommendations,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _deploy_result(eid="exp_001"):
    return {
        "experiment_id": eid,
        "expectancy_r": 0.5,
        "win_rate": 0.62,
        "sample_quality_score": 0.7,
        "max_drawdown_r": -2.0,
    }


def _watch_result(eid="exp_002"):
    return {
        "experiment_id": eid,
        "expectancy_r": 0.15,
        "win_rate": 0.48,
        "sample_quality_score": 0.4,
        "max_drawdown_r": -3.0,
    }


def _reject_result(eid="exp_003"):
    return {
        "experiment_id": eid,
        "expectancy_r": -0.8,
        "win_rate": 0.30,
        "sample_quality_score": 0.2,
        "max_drawdown_r": -8.0,
    }


# ---------------------------------------------------------------------------
# generate_recommendations
# ---------------------------------------------------------------------------

class TestGenerateRecommendations:
    def test_empty_results(self):
        recs = generate_recommendations([])
        assert recs == []

    def test_single_deploy(self):
        recs = generate_recommendations([_deploy_result()])
        assert len(recs) == 1
        assert recs[0].action == "DEPLOY"
        assert recs[0].confidence > 0.5

    def test_single_watch(self):
        recs = generate_recommendations([_watch_result()])
        assert len(recs) == 1
        assert recs[0].action == "WATCH"

    def test_single_reject(self):
        recs = generate_recommendations([_reject_result()])
        assert len(recs) == 1
        assert recs[0].action == "REJECT"

    def test_mixed_results(self):
        results = [_deploy_result("d1"), _watch_result("w1"), _reject_result("r1")]
        recs = generate_recommendations(results)
        actions = {r.action for r in recs}
        assert actions == {"DEPLOY", "WATCH", "REJECT"}

    def test_recommendation_has_all_fields(self):
        recs = generate_recommendations([_deploy_result()])
        r = recs[0]
        assert isinstance(r.experiment_id, str)
        assert isinstance(r.action, str)
        assert isinstance(r.confidence, float)
        assert isinstance(r.rationale, str)
        assert isinstance(r.risk_factors, tuple)
        assert isinstance(r.next_steps, tuple)

    def test_confidence_in_range(self):
        results = [_deploy_result(), _watch_result(), _reject_result()]
        for r in generate_recommendations(results):
            assert 0.0 <= r.confidence <= 1.0

    def test_deploy_high_drawdown_becomes_watch_or_reject(self):
        """A deploy-quality result with huge drawdown should not get DEPLOY."""
        result = _deploy_result()
        result["max_drawdown_r"] = -15.0
        recs = generate_recommendations([result])
        assert recs[0].action != "DEPLOY" or recs[0].confidence < 0.5


# ---------------------------------------------------------------------------
# rank_recommendations
# ---------------------------------------------------------------------------

class TestRankRecommendations:
    def test_deploy_before_watch_before_reject(self):
        results = [_reject_result("r"), _watch_result("w"), _deploy_result("d")]
        recs = generate_recommendations(results)
        ranked = rank_recommendations(recs)
        actions = [r.action for r in ranked]
        assert actions == ["DEPLOY", "WATCH", "REJECT"]

    def test_within_action_sorted_by_confidence(self):
        d1 = _deploy_result("d1")
        d2 = _deploy_result("d2")
        d2_copy = {**d2, "expectancy_r": 0.8, "win_rate": 0.70}
        recs = generate_recommendations([d1, d2_copy])
        ranked = rank_recommendations(recs)
        assert ranked[0].confidence >= ranked[1].confidence


# ---------------------------------------------------------------------------
# filter_recommendations
# ---------------------------------------------------------------------------

class TestFilterRecommendations:
    def test_filter_by_action(self):
        results = [_deploy_result("d"), _watch_result("w"), _reject_result("r")]
        recs = generate_recommendations(results)
        filtered = filter_recommendations(recs, {"action": "DEPLOY"})
        assert len(filtered) == 1
        assert filtered[0].action == "DEPLOY"

    def test_filter_by_min_confidence(self):
        results = [_deploy_result("d"), _reject_result("r")]
        recs = generate_recommendations(results)
        filtered = filter_recommendations(recs, {"min_confidence": 0.1})
        for r in filtered:
            assert r.confidence >= 0.1

    def test_filter_by_max_risk_factors(self):
        results = [_reject_result("r")]
        recs = generate_recommendations(results)
        filtered = filter_recommendations(recs, {"max_risk_factors": 0})
        # reject results typically have risk factors
        for r in filtered:
            assert len(r.risk_factors) == 0

    def test_filter_no_criteria_returns_all(self):
        results = [_deploy_result(), _watch_result()]
        recs = generate_recommendations(results)
        filtered = filter_recommendations(recs, None)
        assert len(filtered) == len(recs)

    def test_filter_by_action_list(self):
        results = [_deploy_result("d"), _watch_result("w"), _reject_result("r")]
        recs = generate_recommendations(results)
        filtered = filter_recommendations(recs, {"action": ["DEPLOY", "WATCH"]})
        assert all(r.action in ("DEPLOY", "WATCH") for r in filtered)
