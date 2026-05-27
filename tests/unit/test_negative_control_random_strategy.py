"""Tests for negative control random strategy — T7041-T7080.

Seeded random, deterministic tests.
"""
from __future__ import annotations

import pytest
from core.negative_control_random_strategy import generate_random_strategy_baseline


class TestRandomStrategyNormal:
    def test_generates_baseline(self):
        result = generate_random_strategy_baseline(100, seed=42)
        assert result["baseline_type"] == "random_strategy"
        assert result["trade_count"] > 0

    def test_has_score(self):
        result = generate_random_strategy_baseline(100, seed=42)
        assert "score" in result


class TestRandomStrategyEdge:
    def test_small_bars(self):
        result = generate_random_strategy_baseline(10, seed=42)
        assert result["total_bars"] == 10


class TestRandomStrategyDeterministic:
    def test_same_seed_same_result(self):
        r1 = generate_random_strategy_baseline(100, seed=42)
        r2 = generate_random_strategy_baseline(100, seed=42)
        assert r1["trade_count"] == r2["trade_count"]
        assert r1["total_pnl"] == r2["total_pnl"]

    def test_different_seed_different_result(self):
        r1 = generate_random_strategy_baseline(100, seed=42)
        r2 = generate_random_strategy_baseline(100, seed=99)
        # Very unlikely to be identical
        assert r1["total_pnl"] != r2["total_pnl"] or r1["trade_count"] != r2["trade_count"]


class TestRandomStrategySafetyBoundary:
    def test_baseline_safety(self):
        r = generate_random_strategy_baseline(100, seed=42)
        assert r["release_hold"] == "HOLD"
        assert r["advisory_only"] is True
        assert r["human_review_required"] is True
