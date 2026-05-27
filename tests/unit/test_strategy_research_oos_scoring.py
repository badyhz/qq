"""Tests for out-of-sample scoring — T4711-T4740."""
from __future__ import annotations

import pytest

from core.strategy_research_oos_scoring import (
    OOSScore,
    compute_oos_score,
    oos_score_to_dict,
)


class TestOOSScoring:
    def test_good_scores_no_flags(self):
        score = compute_oos_score(
            "test", "ps1", "BTCUSDT", "5m",
            train_score=0.8, validation_score=0.75, test_score=0.7,
            train_trades=20, validation_trades=20, test_trades=20,
        )
        assert score.overfit_flag is False
        assert score.degradation_flag is False
        assert score.sample_size_warning is False
        assert score.promotion_score > 0

    def test_degradation_flag(self):
        score = compute_oos_score(
            "test", "ps1", "BTCUSDT", "5m",
            train_score=0.9, validation_score=0.2, test_score=0.1,
            train_trades=20, validation_trades=20, test_trades=20,
        )
        assert score.degradation_flag is True

    def test_overfit_flag(self):
        score = compute_oos_score(
            "test", "ps1", "BTCUSDT", "5m",
            train_score=0.95, validation_score=0.2, test_score=0.2,
            train_trades=20, validation_trades=20, test_trades=20,
        )
        assert score.overfit_flag is True

    def test_sample_size_warning(self):
        score = compute_oos_score(
            "test", "ps1", "BTCUSDT", "5m",
            train_score=0.8, validation_score=0.7, test_score=0.6,
            train_trades=2, validation_trades=2, test_trades=2,
        )
        assert score.sample_size_warning is True

    def test_stability_penalty_high_variance(self):
        score = compute_oos_score(
            "test", "ps1", "BTCUSDT", "5m",
            train_score=0.9, validation_score=0.1, test_score=0.5,
            train_trades=20, validation_trades=20, test_trades=20,
        )
        assert score.stability_penalty > 0

    def test_overfit_reduces_promotion_score(self):
        good = compute_oos_score("test", "ps1", "BTCUSDT", "5m",
                                 0.8, 0.75, 0.7, 20, 20, 20)
        overfit = compute_oos_score("test", "ps1", "BTCUSDT", "5m",
                                    0.95, 0.2, 0.2, 20, 20, 20)
        assert overfit.promotion_score < good.promotion_score


class TestOOSSerialization:
    def test_to_dict(self):
        score = compute_oos_score("test", "ps1", "BTC", "5m", 0.8, 0.7, 0.6)
        d = oos_score_to_dict(score)
        assert d["strategy_id"] == "test"
        assert "promotion_score" in d
        assert isinstance(d["overfit_flag"], bool)
