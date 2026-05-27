"""Tests for parameter sensitivity ranking — T6121-T6160.

Single/multi-param perturbation tests.
"""
from __future__ import annotations

import pytest
from core.parameter_sensitivity_ranking import (
    compute_sensitivity_ranking, build_sensitivity_ranking_report,
)


class TestSensitivityRankingNormal:
    def test_basic_ranking(self):
        rankings = compute_sensitivity_ranking(0.5, {"a": [0.4, 0.6], "b": [0.45, 0.55]})
        assert len(rankings) == 2
        assert rankings[0].rank == 1

    def test_build_report(self):
        rankings = compute_sensitivity_ranking(0.5, {"a": [0.4, 0.6]})
        report = build_sensitivity_ranking_report(rankings, seed=42)
        assert report["verdict"] == "PASS"


class TestSensitivityRankingDeterministic:
    def test_deterministic(self):
        r1 = compute_sensitivity_ranking(0.5, {"a": [0.4, 0.6]})
        r2 = compute_sensitivity_ranking(0.5, {"a": [0.4, 0.6]})
        assert r1 == r2
