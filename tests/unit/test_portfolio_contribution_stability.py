"""Tests for portfolio contribution stability — T6801-T6840.

Stable vs one-strategy dominance tests.
"""
from __future__ import annotations

import pytest
from core.portfolio_contribution_stability import assess_contribution_stability


class TestContributionStabilityNormal:
    def test_balanced_contribution(self):
        r = assess_contribution_stability({"a": 0.5, "b": 0.5})
        assert r["stable"]


class TestContributionStabilityAdversarial:
    def test_dominant_strategy(self):
        r = assess_contribution_stability({"a": 0.9, "b": 0.1})
        assert not r["stable"]
        assert "DOMINANT_STRATEGY" in r["warning"]


class TestContributionStabilityEdge:
    def test_empty(self):
        r = assess_contribution_stability({})
        assert not r["stable"]
