"""Tests for parameter fragility report — T5961-T6000.

Stable, fragile, sparse fixtures.
"""
from __future__ import annotations

import pytest
from core.parameter_fragility_report import compute_fragility, build_fragility_report


class TestFragilityNormal:
    def test_stable_strategy(self):
        r = compute_fragility("strat1", 0.5, [0.48, 0.49, 0.50, 0.51, 0.52])
        assert not r.is_fragile
        assert r.fragility_score < 0.4

    def test_fragile_strategy(self):
        r = compute_fragility("strat1", 0.5, [0.0, 1.0, 0.0, 1.0, 0.0])
        assert r.is_fragile


class TestFragilityEdge:
    def test_empty_neighborhood(self):
        r = compute_fragility("strat1", 0.5, [])
        assert r.is_fragile

    def test_single_score(self):
        r = compute_fragility("strat1", 0.5, [0.5])
        assert not r.is_fragile


class TestFragilityAdversarial:
    def test_nan_scores(self):
        r = compute_fragility("strat1", 0.5, [float("nan"), float("nan")])
        assert r.is_fragile


class TestFragilityDeterministic:
    def test_deterministic_report(self):
        results = [compute_fragility("s1", 0.5, [0.4, 0.5, 0.6])]
        r1 = build_fragility_report(results, seed=42)
        r2 = build_fragility_report(results, seed=42)
        # Compare without generated_at
        r1_copy = {k: v for k, v in r1.items() if k != "generated_at"}
        r2_copy = {k: v for k, v in r2.items() if k != "generated_at"}
        assert r1_copy == r2_copy


class TestFragilitySafetyBoundary:
    def test_report_safety(self):
        r = build_fragility_report([], seed=42)
        assert r["release_hold"] == "HOLD"
        assert r["advisory_only"] is True
