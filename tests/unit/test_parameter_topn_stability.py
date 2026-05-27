"""Tests for parameter top-N stability — T6081-T6120.

Rank swap, stable rank, dominance failure tests.
"""
from __future__ import annotations

import pytest
from core.parameter_topn_stability import compute_topn_stability, topn_to_dict


class TestTopNStabilityNormal:
    def test_stable_rank(self):
        r = compute_topn_stability("s1", [1, 1, 1, 1, 1])
        assert r.stable_rank
        assert r.dominant

    def test_unstable_rank(self):
        r = compute_topn_stability("s1", [1, 5, 1, 5, 1])
        assert not r.stable_rank


class TestTopNStabilityEdge:
    def test_empty_history(self):
        r = compute_topn_stability("s1", [])
        assert not r.stable_rank


class TestTopNStabilityDeterministic:
    def test_deterministic(self):
        r1 = topn_to_dict(compute_topn_stability("s1", [1, 2, 3]))
        r2 = topn_to_dict(compute_topn_stability("s1", [1, 2, 3]))
        assert r1 == r2
