"""Tests for strategy research promotion policy — T4741-T4770."""
from __future__ import annotations

import pytest

from core.strategy_research_oos_scoring import OOSScore, compute_oos_score
from core.strategy_research_promotion import (
    PromotionRecommendation,
    evaluate_promotion,
    promotion_to_dict,
)


def _make_oos(train=0.8, val=0.75, test=0.7, overfit=False, degradation=False, sample_warn=False):
    return OOSScore(
        strategy_id="test", parameter_set_id="ps1", symbol="BTCUSDT", timeframe="5m",
        train_score=train, validation_score=val, test_score=test,
        stability_penalty=0.1, overfit_flag=overfit, degradation_flag=degradation,
        sample_size_warning=sample_warn, promotion_score=0.5,
    )


class TestPromotion:
    def test_promote_good_score(self):
        oos = _make_oos()
        rec = evaluate_promotion(oos)
        assert rec.status == "PROMOTE_TO_NEXT_RESEARCH_ROUND"
        assert rec.release_hold == "HOLD"

    def test_reject_overfit(self):
        oos = _make_oos(overfit=True)
        rec = evaluate_promotion(oos)
        assert rec.status == "REJECT_OVERFIT"
        assert "OVERFIT" in rec.blocking_risks

    def test_reject_degradation(self):
        oos = _make_oos(degradation=True)
        rec = evaluate_promotion(oos)
        assert rec.status == "REJECT_OVERFIT"

    def test_reject_drawdown(self):
        oos = _make_oos()
        rec = evaluate_promotion(oos, max_drawdown=0.2, max_drawdown_limit=0.15)
        assert rec.status == "REJECT_DRAWDOWN"
        assert "DRAWDOWN" in rec.blocking_risks

    def test_watch_small_sample(self):
        oos = _make_oos(sample_warn=True)
        rec = evaluate_promotion(oos)
        assert rec.status in ("WATCH_MORE_DATA", "REJECT_OVERFIT")

    def test_human_review_high_stability_penalty(self):
        oos = OOSScore(
            strategy_id="test", parameter_set_id="ps1", symbol="BTCUSDT", timeframe="5m",
            train_score=0.8, validation_score=0.75, test_score=0.7,
            stability_penalty=0.8, overfit_flag=False, degradation_flag=False,
            sample_size_warning=False, promotion_score=0.5,
        )
        rec = evaluate_promotion(oos)
        assert rec.status == "HUMAN_REVIEW_REQUIRED"
        assert rec.human_review_required is True

    def test_release_hold_always(self):
        for oos in [_make_oos(), _make_oos(overfit=True), _make_oos(degradation=True)]:
            rec = evaluate_promotion(oos)
            assert rec.release_hold == "HOLD"

    def test_keep_hold_default(self):
        """All recommendations are ultimately KEEP_HOLD at manifest level."""
        oos = _make_oos()
        rec = evaluate_promotion(oos)
        assert rec.release_hold == "HOLD"


class TestPromotionSerialization:
    def test_to_dict(self):
        oos = _make_oos()
        rec = evaluate_promotion(oos)
        d = promotion_to_dict(rec)
        assert d["release_hold"] == "HOLD"
        assert d["status"] in [
            "PROMOTE_TO_NEXT_RESEARCH_ROUND", "WATCH_MORE_DATA",
            "REJECT_OVERFIT", "REJECT_DRAWDOWN", "HUMAN_REVIEW_REQUIRED", "KEEP_HOLD",
        ]
