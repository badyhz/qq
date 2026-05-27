"""Tests for strategy sparse/noisy handling — T6521-T6560.

Sparse, noisy, adverse fixtures.
"""
from __future__ import annotations

import pytest
from core.strategy_sparse_noisy_handling import assess_signal_quality, assess_adverse_fixture


class TestSparseNoisyNormal:
    def test_sufficient_signal(self):
        r = assess_signal_quality("s1", 100, 1000)
        assert r["sufficient_evidence"]


class TestSparseNoisyAdversarial:
    def test_sparse_signal(self):
        r = assess_signal_quality("s1", 1, 10000)
        assert r["is_sparse"]
        assert not r["sufficient_evidence"]

    def test_zero_signals(self):
        r = assess_signal_quality("s1", 0, 1000)
        assert "ZERO_SIGNALS" in r["warnings"]

    def test_adverse_degradation(self):
        r = assess_adverse_fixture("s1", 0.5, 0.1)
        assert r["degradation_detected"]
