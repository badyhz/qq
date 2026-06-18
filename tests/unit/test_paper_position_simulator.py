"""Tests for paper position simulator — TP/SL/PnL/timeout logic."""
from __future__ import annotations

import os
import py_compile

import pytest

from core.paper_trading.paper_position_simulator import (
    simulate_intent_only, simulate_with_klines, _calc_pnl, _update_position,
)
from core.paper_trading.paper_position import open_position
from core.paper_trading.data_source import MarketBar

MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "..",
                           "core", "paper_trading", "paper_position_simulator.py")


def _make_intent(**overrides):
    intent = {
        "intent_id": "TI_test",
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
        "position_size_preview": 100.0,
        "max_risk_pct": 0.5,
        "risk_gate_status": "PASS",
    }
    intent.update(overrides)
    return intent


def _make_long_intent(**overrides):
    intent = {
        "intent_id": "TI_long",
        "date": "2026-06-18",
        "strategy_id": "macd_rebound_watch",
        "strategy_type": "macd_rebound_watch",
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "side": "LONG",
        "intent_status": "SHADOW_READY",
        "execution_mode": "shadow_only",
        "entry_price": 60000.0,
        "stop_loss": 59000.0,
        "take_profit": 62000.0,
        "rr_ratio": 2.0,
        "position_size_preview": 0.5,
        "max_risk_pct": 0.5,
        "risk_gate_status": "PASS",
    }
    intent.update(overrides)
    return intent


def _make_bar(symbol, timeframe, open_p, high, low, close):
    return MarketBar(
        timestamp=0, open=open_p, high=high, low=low, close=close,
        volume=1000.0, symbol=symbol, timeframe=timeframe,
    )


class TestModuleCompiles:
    def test_compiles(self):
        py_compile.compile(MODULE_PATH, doraise=True)


class TestIntentOnly:
    def test_creates_open_position(self):
        result = simulate_intent_only([_make_intent()], "2026-06-18")
        assert result.position_count == 1
        assert result.open_count == 1
        assert result.positions[0]["status"] == "OPEN"

    def test_skips_blocked_intent(self):
        intent = _make_intent(intent_status="BLOCKED_BY_RISK_GATE")
        result = simulate_intent_only([intent], "2026-06-18")
        assert result.position_count == 0
        assert result.invalid_count == 1

    def test_skips_invalid_intent(self):
        intent = _make_intent(intent_status="INVALID")
        result = simulate_intent_only([intent], "2026-06-18")
        assert result.position_count == 0

    def test_empty_intents(self):
        result = simulate_intent_only([], "2026-06-18")
        assert result.position_count == 0
        assert result.mode == "intent_only"

    def test_multiple_intents(self):
        intents = [_make_intent(), _make_long_intent()]
        result = simulate_intent_only(intents, "2026-06-18")
        assert result.position_count == 2


class TestWithKlines:
    def test_short_sl_hit(self):
        pos = open_position(_make_intent())
        # SHORT: SL=1.18, TP=1.09. Bar high >= 1.18 → SL hit
        bars = [_make_bar("XRPUSDT", "15m", 1.16, 1.19, 1.14, 1.17)]
        updated = _update_position(pos, bars, 24)
        assert updated["status"] == "STOP_LOSS_HIT"
        assert updated["exit_price"] == 1.18

    def test_short_tp_hit(self):
        pos = open_position(_make_intent())
        # SHORT: SL=1.18, TP=1.09. Bar low <= 1.09 → TP hit
        bars = [_make_bar("XRPUSDT", "15m", 1.12, 1.13, 1.08, 1.10)]
        updated = _update_position(pos, bars, 24)
        assert updated["status"] == "TAKE_PROFIT_HIT"
        assert updated["exit_price"] == 1.09

    def test_long_sl_hit(self):
        pos = open_position(_make_long_intent())
        # LONG: SL=59000. Bar low <= 59000 → SL hit
        bars = [_make_bar("BTCUSDT", "15m", 60000, 60500, 58500, 59500)]
        updated = _update_position(pos, bars, 24)
        assert updated["status"] == "STOP_LOSS_HIT"
        assert updated["exit_price"] == 59000.0

    def test_long_tp_hit(self):
        pos = open_position(_make_long_intent())
        # LONG: TP=62000. Bar high >= 62000 → TP hit
        bars = [_make_bar("BTCUSDT", "15m", 60000, 62500, 59800, 61500)]
        updated = _update_position(pos, bars, 24)
        assert updated["status"] == "TAKE_PROFIT_HIT"
        assert updated["exit_price"] == 62000.0

    def test_sl_takes_priority_over_tp(self):
        pos = open_position(_make_intent())
        # Bar hits both SL (high >= 1.18) and TP (low <= 1.09)
        bars = [_make_bar("XRPUSDT", "15m", 1.15, 1.20, 1.05, 1.12)]
        updated = _update_position(pos, bars, 24)
        assert updated["status"] == "STOP_LOSS_HIT"

    def test_stays_open(self):
        pos = open_position(_make_intent())
        # Bar doesn't hit SL or TP
        bars = [_make_bar("XRPUSDT", "15m", 1.15, 1.16, 1.13, 1.14)]
        updated = _update_position(pos, bars, 24)
        assert updated["status"] == "OPEN"

    def test_timeout(self):
        pos = open_position(_make_intent())
        # 30 bars but timeout at 24
        bars = [_make_bar("XRPUSDT", "15m", 1.15, 1.16, 1.13, 1.14)] * 30
        updated = _update_position(pos, bars, 24)
        assert updated["status"] == "TIMEOUT_EXIT"

    def test_pnl_short_tp(self):
        pos = open_position(_make_intent())
        # SHORT entry=1.15, TP=1.09, size=100
        # pnl = (1.15 - 1.09) * 100 = 6.0
        bars = [_make_bar("XRPUSDT", "15m", 1.12, 1.13, 1.08, 1.10)]
        updated = _update_position(pos, bars, 24)
        assert updated["status"] == "TAKE_PROFIT_HIT"
        assert abs(updated["realized_pnl"] - 6.0) < 0.01

    def test_pnl_short_sl(self):
        pos = open_position(_make_intent())
        # SHORT entry=1.15, SL=1.18, size=100
        # pnl = (1.15 - 1.18) * 100 = -3.0
        bars = [_make_bar("XRPUSDT", "15m", 1.16, 1.19, 1.14, 1.17)]
        updated = _update_position(pos, bars, 24)
        assert updated["status"] == "STOP_LOSS_HIT"
        assert abs(updated["realized_pnl"] - (-3.0)) < 0.01

    def test_r_multiple(self):
        pos = open_position(_make_intent())
        # SHORT entry=1.15, SL=1.18, TP=1.09, size=100
        # risk_amount = abs(1.15-1.18)*100 = 3.0
        # TP pnl = 6.0
        # r = 6.0 / 3.0 = 2.0
        bars = [_make_bar("XRPUSDT", "15m", 1.12, 1.13, 1.08, 1.10)]
        updated = _update_position(pos, bars, 24)
        assert abs(updated["r_multiple"] - 2.0) < 0.01


class TestSimulateWithKlines:
    def test_full_simulation(self):
        intents = [_make_intent()]
        bars_map = {
            "XRPUSDT_15m": [_make_bar("XRPUSDT", "15m", 1.12, 1.13, 1.08, 1.10)],
        }
        result = simulate_with_klines(intents, bars_map, "2026-06-18")
        assert result.position_count == 1
        assert result.tp_hit_count == 1

    def test_no_matching_bars(self):
        intents = [_make_intent()]
        result = simulate_with_klines(intents, {}, "2026-06-18")
        assert result.position_count == 1
        assert result.open_count == 1


class TestCalcPnl:
    def test_long_profit(self):
        assert _calc_pnl("LONG", 100, 110, 1) == 10.0

    def test_long_loss(self):
        assert _calc_pnl("LONG", 100, 90, 1) == -10.0

    def test_short_profit(self):
        assert _calc_pnl("SHORT", 100, 90, 1) == 10.0

    def test_short_loss(self):
        assert _calc_pnl("SHORT", 100, 110, 1) == -10.0


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
