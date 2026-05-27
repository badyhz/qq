"""Tests for strategy symbol sensitivity — T6401-T6440.

Single-symbol, concentrated, broad symbol tests.
"""
from __future__ import annotations

import pytest
from core.strategy_symbol_sensitivity import compute_symbol_sensitivity


class TestSymbolSensitivityNormal:
    def test_broad_symbols(self):
        r = compute_symbol_sensitivity("s1", {"BTCUSDT": 0.5, "ETHUSDT": 0.5})
        assert r["concentration"] < 0.7


class TestSymbolSensitivityEdge:
    def test_single_symbol(self):
        r = compute_symbol_sensitivity("s1", {"BTCUSDT": 1.0})
        assert r["concentration"] == 1.0
        assert "SINGLE_SYMBOL" in r["warning"]
