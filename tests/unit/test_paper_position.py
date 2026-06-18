"""Tests for paper position model — open_position, validation, lifecycle."""
from __future__ import annotations

import os
import py_compile

import pytest

from core.paper_trading.paper_position import (
    open_position, dict_to_position, PaperPosition,
    POSITION_SAFETY_FLAGS, CLOSED_STATUSES,
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
        assert open_position(_make_intent(intent_status="BLOCKED_BY_RISK_GATE")) is None

    def test_rejects_invalid(self):
        assert open_position(_make_intent(intent_status="INVALID")) is None

    def test_rejects_no_trade(self):
        assert open_position(_make_intent(side="NO_TRADE")) is None

    def test_rejects_non_shadow_mode(self):
        assert open_position(_make_intent(execution_mode="live")) is None

    def test_rejects_zero_entry(self):
        assert open_position(_make_intent(entry_price=0)) is None

    def test_rejects_zero_sl(self):
        assert open_position(_make_intent(stop_loss=0)) is None

    def test_rejects_zero_tp(self):
        assert open_position(_make_intent(take_profit=0)) is None

    def test_position_has_id(self):
        pos = open_position(_make_intent())
        assert pos.position_id.startswith("PP_")

    def test_safety_flags(self):
        pos = open_position(_make_intent())
        for flag in ["PAPER_ONLY", "SHADOW_ONLY", "NO_ORDER", "NO_REAL_ORDER"]:
            assert flag in pos.safety_flags

    def test_lifecycle_mode(self):
        pos = open_position(_make_intent())
        assert pos.lifecycle_mode == "future_only"

    def test_opened_bar_time_set(self):
        pos = open_position(_make_intent())
        assert pos.opened_bar_time is not None
        assert pos.opened_bar_time > 0

    def test_to_dict_has_lifecycle_fields(self):
        pos = open_position(_make_intent())
        d = pos.to_dict()
        assert "lifecycle_mode" in d
        assert "opened_bar_time" in d
        assert "last_checked_at" in d
        assert "last_checked_bar_time" in d


class TestDictToPosition:
    def test_roundtrip(self):
        pos = open_position(_make_intent())
        d = pos.to_dict()
        pos2 = dict_to_position(d)
        assert pos2.position_id == pos.position_id
        assert pos2.intent_id == pos.intent_id
        assert pos2.side == pos.side
        assert pos2.status == pos.status
        assert pos2.lifecycle_mode == "future_only"

    def test_defaults_for_missing_fields(self):
        d = _make_intent()
        d["position_id"] = "PP_test"
        d["intent_id"] = "TI_test"
        d["source"] = "trade_intent"
        d["status"] = "OPEN"
        d["entry_price"] = 1.0
        d["stop_loss"] = 0.9
        d["take_profit"] = 1.1
        d["position_size_preview"] = 1.0
        d["max_risk_pct"] = 0.5
        d["paper_equity_preview"] = 10000.0
        d["opened_at"] = "2026-01-01"
        d["created_at"] = "2026-01-01"
        pos = dict_to_position(d)
        assert pos.lifecycle_mode == "future_only"


class TestClosedStatuses:
    def test_closed_statuses(self):
        assert "TAKE_PROFIT_HIT" in CLOSED_STATUSES
        assert "STOP_LOSS_HIT" in CLOSED_STATUSES
        assert "TIMEOUT_EXIT" in CLOSED_STATUSES
        assert "INVALID" in CLOSED_STATUSES
        assert "OPEN" not in CLOSED_STATUSES


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
