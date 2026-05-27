"""Tests for negative control shuffled returns — T7081-T7120.

Shuffle seed, deterministic tests.
"""
from __future__ import annotations

import pytest
from core.negative_control_shuffled_returns import generate_shuffled_returns_baseline


class TestShuffledReturnsNormal:
    def test_generates_baseline(self):
        result = generate_shuffled_returns_baseline([0.1, 0.2, 0.3], seed=42)
        assert result["baseline_type"] == "shuffled_returns"
        assert result["sample_count"] == 3


class TestShuffledReturnsEdge:
    def test_empty_returns(self):
        result = generate_shuffled_returns_baseline([], seed=42)
        assert result["sample_count"] == 0


class TestShuffledReturnsDeterministic:
    def test_same_seed_same_result(self):
        returns = [0.1, 0.2, -0.1, 0.05, 0.15]
        r1 = generate_shuffled_returns_baseline(returns, seed=42)
        r2 = generate_shuffled_returns_baseline(returns, seed=42)
        assert r1["total_return"] == r2["total_return"]


class TestShuffledReturnsSafetyBoundary:
    def test_baseline_safety(self):
        r = generate_shuffled_returns_baseline([0.1], seed=42)
        assert r["release_hold"] == "HOLD"
        assert r["advisory_only"] is True
