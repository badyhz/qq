"""Tests for strategy entry/exit diagnostics — T6481-T6520.

Normal, no-exit, adverse exit tests.
"""
from __future__ import annotations

import pytest
from core.strategy_entry_exit_diagnostics import compute_entry_exit_diagnostics


class TestEntryExitNormal:
    def test_normal_trades(self):
        trades = [{"hold_bars": 10, "exit_type": "take_profit"}] * 5
        r = compute_entry_exit_diagnostics("s1", trades)
        assert r["trade_count"] == 5
        assert r["avg_hold_bars"] == 10


class TestEntryExitEdge:
    def test_no_trades(self):
        r = compute_entry_exit_diagnostics("s1", [])
        assert r["trade_count"] == 0
        assert "NO_TRADES" in r["warnings"]


class TestEntryExitAdversarial:
    def test_high_no_exit(self):
        trades = [{"hold_bars": 10, "exit_type": "no_exit"}] * 10
        r = compute_entry_exit_diagnostics("s1", trades)
        assert "HIGH_NO_EXIT_RATE" in r["warnings"]
