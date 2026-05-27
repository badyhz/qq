"""Tests for strategy regime sensitivity — T6361-T6400.

Trend/chop/volatility fixtures.
"""
from __future__ import annotations

import pytest
from core.strategy_regime_sensitivity import compute_regime_sensitivity


class TestRegimeSensitivityNormal:
    def test_balanced_regime(self):
        r = compute_regime_sensitivity("s1", {"TREND": 0.5, "CHOP": 0.5, "VOLATILE": 0.5})
        assert r["sensitivity"] == 0.0


class TestRegimeSensitivityEdge:
    def test_no_regimes(self):
        r = compute_regime_sensitivity("s1", {})
        assert r["warning"] == "NO_REGIME_DATA"


class TestRegimeSensitivityAdversarial:
    def test_high_sensitivity(self):
        r = compute_regime_sensitivity("s1", {"TREND": 1.0, "CHOP": 0.0})
        assert r["sensitivity"] > 0.5
