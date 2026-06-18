"""Tests for paper position model — open_position, validation, PnL."""
from __future__ import annotations

import os
import py_compile

import pytest

from core.paper_trading.paper_position import (
    open_position, PaperPosition, POSITION_SAFETY_FLAGS,
)

MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "..",
                           "core", "paper_trading", "paper_position.py")


def _make_intent(**overrides):
    intent = {
        "intent_id": "TI_test123",
        "date": "2026-06-18",
        "strategy_id": "weak_short_watch",
        "strategy_type": "weak_short_watch",
        "symbol": "XRPUSDT",
        "timeframe": "15m",
        "side": "SHORT",
        "intent_status": "SHADOW_READY",
        "execution_mode": "shadow_only",
        "entry_price": 1.15,
        "stop_loss": 1.18,
        "take_profit": 1.09,
        "rr_ratio": 2.0,
        "risk_distance_pct": 2.61,
        "reward_distance_pct": 5.22,
        "position_size_preview": 0.5,
        "max_risk_pct": 0.5,
        "risk_gate_status": "PASS",
    }
    intent.update(overrides)
    return intent


class TestModuleCompiles:
    def test_compiles(self):
        py_compile.compile(MODULE_PATH, doraise=True)


class TestOpenPosition:
    def test_shadow_ready_short(self):
        pos = open_position(_make_intent())
        assert pos is not None
        assert pos.side == "SHORT"
        assert pos.status == "OPEN"

    def test_shadow_ready_long(self):
        intent = _make_intent(
            side="LONG", entry_price=60000.0,
            stop_loss=59000.0, take_profit=62000.0,
        )
        pos = open_position(intent)
        assert pos is not None
        assert pos.side == "LONG"
        assert pos.status == "OPEN"

    def test_rejects_blocked(self):
        pos = open_position(_make_intent(intent_status="BLOCKED_BY_RISK_GATE"))
        assert pos is None

    def test_rejects_invalid(self):
        pos = open_position(_make_intent(intent_status="INVALID"))
        assert pos is None

    def test_rejects_no_trade(self):
        pos = open_position(_make_intent(side="NO_TRADE"))
        assert pos is None

    def test_rejects_non_shadow_mode(self):
        pos = open_position(_make_intent(execution_mode="live"))
        assert pos is None

    def test_rejects_zero_entry(self):
        pos = open_position(_make_intent(entry_price=0))
        assert pos is None

    def test_rejects_zero_sl(self):
        pos = open_position(_make_intent(stop_loss=0))
        assert pos is None

    def test_rejects_zero_tp(self):
        pos = open_position(_make_intent(take_profit=0))
        assert pos is None

    def test_position_has_id(self):
        pos = open_position(_make_intent())
        assert pos.position_id.startswith("PP_")

    def test_safety_flags(self):
        pos = open_position(_make_intent())
        for flag in ["PAPER_ONLY", "SHADOW_ONLY", "NO_ORDER", "NO_REAL_ORDER"]:
            assert flag in pos.safety_flags

    def test_to_dict(self):
        pos = open_position(_make_intent())
        d = pos.to_dict()
        assert d["side"] == "SHORT"
        assert d["status"] == "OPEN"
        assert d["unrealized_pnl"] == 0.0
        assert d["realized_pnl"] == 0.0


class TestNoForbiddenPatterns:
    def test_no_order_words(self):
        with open(MODULE_PATH) as f:
            content = f.read()
        for word in ["submit_order", "place_order", "cancel_order", "execute_trade"]:
            assert word not in content

    def test_no_env_reads(self):
        with open(MODULE_PATH) as f:
            content = f.read()
        assert "os.environ" not in content
        assert "os.getenv" not in content
