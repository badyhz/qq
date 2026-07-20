"""Tests for paper position simulator — future-only, dedup, TP/SL/PnL."""
from __future__ import annotations

import os
import py_compile

import pytest

from core.paper_trading.paper_position_simulator import (
    simulate_intent_only, simulate_with_klines,
    simulate_existing_positions_update_only, _calc_pnl, _update_position,
)
from core.paper_trading.paper_position import open_position, dict_to_position
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


def _make_bar(symbol, timeframe, open_p, high, low, close, timestamp=1000):
    return MarketBar(
        timestamp=timestamp, open=open_p, high=high, low=low, close=close,
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
        result = simulate_intent_only([_make_intent(intent_status="BLOCKED_BY_RISK_GATE")], "2026-06-18")
        assert result.position_count == 0

    def test_skips_invalid_intent(self):
        result = simulate_intent_only([_make_intent(intent_status="INVALID")], "2026-06-18")
        assert result.position_count == 0

    def test_empty_intents(self):
        result = simulate_intent_only([], "2026-06-18")
        assert result.position_count == 0
        assert result.mode == "intent_only"

    def test_multiple_intents(self):
        result = simulate_intent_only([_make_intent(), _make_long_intent()], "2026-06-18")
        assert result.position_count == 2

    def test_lifecycle_stats(self):
        result = simulate_intent_only([_make_intent()], "2026-06-18")
        ls = result.lifecycle_stats
        assert ls["new_positions_count"] == 1
        assert ls["existing_positions_count"] == 0
        assert ls["deduped_intents_count"] == 0
        assert ls["future_only"] is True


class TestDedup:
    def test_same_intent_not_duplicated(self):
        r1 = simulate_intent_only([_make_intent()], "2026-06-18")
        r2 = simulate_intent_only([_make_intent()], "2026-06-18", existing_positions=r1.positions)
        assert r2.position_count == 1
        assert r2.lifecycle_stats["deduped_intents_count"] == 1

    def test_different_intent_added(self):
        r1 = simulate_intent_only([_make_intent()], "2026-06-18")
        r2 = simulate_intent_only([_make_long_intent()], "2026-06-18", existing_positions=r1.positions)
        assert r2.position_count == 2
        assert r2.lifecycle_stats["new_positions_count"] == 1
        assert r2.lifecycle_stats["existing_positions_count"] == 1


class TestFutureOnly:
    def test_newly_opened_stays_open_with_historical_bars(self):
        """Newly opened position should stay OPEN even if historical bar hits SL."""
        intent = _make_intent()
        r1 = simulate_intent_only([intent], "2026-06-18")
        pos = r1.positions[0]
        # opened_bar_time is recent; use old timestamp bars
        old_bars = [_make_bar("XRPUSDT", "15m", 1.15, 1.20, 1.08, 1.12, timestamp=100)]
        bars_map = {"XRPUSDT_15m": old_bars}
        r2 = simulate_with_klines(
            [_make_intent()], bars_map, "2026-06-18",
            existing_positions=r1.positions,
            newly_opened_ids={pos["position_id"]},
        )
        # Should be skipped as newly opened
        assert r2.positions[0]["status"] == "OPEN"
        assert r2.lifecycle_stats["positions_skipped_newly_opened"] == 1

    def test_future_bars_can_hit_sl(self):
        """Future bars after opened_bar_time can trigger SL."""
        pos = open_position(_make_intent())
        pos_dict = pos.to_dict()
        # Set opened_bar_time to 5000
        pos_dict["opened_bar_time"] = 5000
        # Future bar at 6000 hits SL (high >= 1.18)
        future_bars = [_make_bar("XRPUSDT", "15m", 1.15, 1.19, 1.14, 1.17, timestamp=6000)]
        bars_map = {"XRPUSDT_15m": future_bars}
        r = simulate_with_klines(
            [], bars_map, "2026-06-18",
            existing_positions=[pos_dict],
        )
        assert r.positions[0]["status"] == "STOP_LOSS_HIT"

    def test_future_bars_can_hit_tp(self):
        """Future bars after opened_bar_time can trigger TP."""
        pos = open_position(_make_intent())
        pos_dict = pos.to_dict()
        pos_dict["opened_bar_time"] = 5000
        # Future bar at 6000 hits TP (low <= 1.09)
        future_bars = [_make_bar("XRPUSDT", "15m", 1.12, 1.13, 1.08, 1.10, timestamp=6000)]
        bars_map = {"XRPUSDT_15m": future_bars}
        r = simulate_with_klines(
            [], bars_map, "2026-06-18",
            existing_positions=[pos_dict],
        )
        assert r.positions[0]["status"] == "TAKE_PROFIT_HIT"

    def test_bars_before_opened_bar_time_ignored(self):
        """Bars before opened_bar_time should be filtered out."""
        pos = open_position(_make_intent())
        pos_dict = pos.to_dict()
        pos_dict["opened_bar_time"] = 10000
        # All bars before 10000 — would hit SL but shouldn't be used
        old_bars = [_make_bar("XRPUSDT", "15m", 1.15, 1.20, 1.08, 1.12, timestamp=5000)]
        bars_map = {"XRPUSDT_15m": old_bars}
        r = simulate_with_klines(
            [], bars_map, "2026-06-18",
            existing_positions=[pos_dict],
        )
        assert r.positions[0]["status"] == "OPEN"
        assert r.lifecycle_stats["positions_skipped_no_future_bars"] == 1

    def test_missing_opened_bar_time_skips(self):
        """Missing opened_bar_time should skip update safely."""
        pos = open_position(_make_intent())
        pos_dict = pos.to_dict()
        pos_dict["opened_bar_time"] = None
        bars_map = {"XRPUSDT_15m": [_make_bar("XRPUSDT", "15m", 1.15, 1.20, 1.08, 1.12, timestamp=5000)]}
        r = simulate_with_klines(
            [], bars_map, "2026-06-18",
            existing_positions=[pos_dict],
        )
        assert r.positions[0]["status"] == "OPEN"


class TestClosedImmutability:
    def test_closed_position_stays_closed(self):
        """A closed position should not be updated."""
        pos = open_position(_make_intent())
        pos_dict = pos.to_dict()
        pos_dict["status"] = "STOP_LOSS_HIT"
        pos_dict["closed_at"] = "2026-01-01"
        # New bars that would hit TP
        bars = [_make_bar("XRPUSDT", "15m", 1.12, 1.13, 1.08, 1.10, timestamp=99999)]
        bars_map = {"XRPUSDT_15m": bars}
        r = simulate_with_klines(
            [], bars_map, "2026-06-18",
            existing_positions=[pos_dict],
        )
        assert r.positions[0]["status"] == "STOP_LOSS_HIT"


class TestWithKlines:
    def test_short_sl_hit(self):
        pos = open_position(_make_intent())
        pos_dict = pos.to_dict()
        pos_dict["opened_bar_time"] = 100
        bars = [_make_bar("XRPUSDT", "15m", 1.16, 1.19, 1.14, 1.17, timestamp=200)]
        r = simulate_with_klines([], {"XRPUSDT_15m": bars}, "2026-06-18",
                                 existing_positions=[pos_dict])
        assert r.positions[0]["status"] == "STOP_LOSS_HIT"

    def test_short_tp_hit(self):
        pos = open_position(_make_intent())
        pos_dict = pos.to_dict()
        pos_dict["opened_bar_time"] = 100
        bars = [_make_bar("XRPUSDT", "15m", 1.12, 1.13, 1.08, 1.10, timestamp=200)]
        r = simulate_with_klines([], {"XRPUSDT_15m": bars}, "2026-06-18",
                                 existing_positions=[pos_dict])
        assert r.positions[0]["status"] == "TAKE_PROFIT_HIT"

    def test_long_sl_hit(self):
        pos = open_position(_make_long_intent())
        pos_dict = pos.to_dict()
        pos_dict["opened_bar_time"] = 100
        bars = [_make_bar("BTCUSDT", "15m", 60000, 60500, 58500, 59500, timestamp=200)]
        r = simulate_with_klines([], {"BTCUSDT_15m": bars}, "2026-06-18",
                                 existing_positions=[pos_dict])
        assert r.positions[0]["status"] == "STOP_LOSS_HIT"

    def test_long_tp_hit(self):
        pos = open_position(_make_long_intent())
        pos_dict = pos.to_dict()
        pos_dict["opened_bar_time"] = 100
        bars = [_make_bar("BTCUSDT", "15m", 60000, 62500, 59800, 61500, timestamp=200)]
        r = simulate_with_klines([], {"BTCUSDT_15m": bars}, "2026-06-18",
                                 existing_positions=[pos_dict])
        assert r.positions[0]["status"] == "TAKE_PROFIT_HIT"

    def test_sl_takes_priority_over_tp(self):
        pos = open_position(_make_intent())
        pos_dict = pos.to_dict()
        pos_dict["opened_bar_time"] = 100
        bars = [_make_bar("XRPUSDT", "15m", 1.15, 1.20, 1.05, 1.12, timestamp=200)]
        r = simulate_with_klines([], {"XRPUSDT_15m": bars}, "2026-06-18",
                                 existing_positions=[pos_dict])
        assert r.positions[0]["status"] == "STOP_LOSS_HIT"

    def test_stays_open(self):
        pos = open_position(_make_intent())
        pos_dict = pos.to_dict()
        pos_dict["opened_bar_time"] = 100
        bars = [_make_bar("XRPUSDT", "15m", 1.15, 1.16, 1.13, 1.14, timestamp=200)]
        r = simulate_with_klines([], {"XRPUSDT_15m": bars}, "2026-06-18",
                                 existing_positions=[pos_dict])
        assert r.positions[0]["status"] == "OPEN"

    def test_timeout(self):
        pos = open_position(_make_intent())
        pos_dict = pos.to_dict()
        pos_dict["opened_bar_time"] = 100
        bars = [_make_bar("XRPUSDT", "15m", 1.15, 1.16, 1.13, 1.14, timestamp=200 + i*100) for i in range(30)]
        r = simulate_with_klines([], {"XRPUSDT_15m": bars}, "2026-06-18",
                                 existing_positions=[pos_dict], timeout_bars=24)
        assert r.positions[0]["status"] == "TIMEOUT_EXIT"


class TestCalcPnl:
    def test_long_profit(self):
        assert _calc_pnl("LONG", 100, 110, 1) == 10.0

    def test_long_loss(self):
        assert _calc_pnl("LONG", 100, 90, 1) == -10.0

    def test_short_profit(self):
        assert _calc_pnl("SHORT", 100, 90, 1) == 10.0

    def test_short_loss(self):
        assert _calc_pnl("SHORT", 100, 110, 1) == -10.0


class TestOverlapGuard:
    def test_same_key_blocks_new_position(self):
        """Same strategy+symbol+tf+side OPEN blocks new position."""
        r1 = simulate_intent_only([_make_intent()], "2026-06-18")
        assert r1.position_count == 1
        # Second run with same intent (different intent_id) should be blocked
        intent2 = _make_intent(intent_id="TI_overlap")
        r2 = simulate_intent_only([intent2], "2026-06-18", existing_positions=r1.positions)
        assert r2.position_count == 1  # no new position
        assert r2.lifecycle_stats["positions_skipped_overlap_open"] == 1

    def test_closed_position_does_not_block(self):
        """Closed position does not block new position with same key."""
        pos = open_position(_make_intent())
        pos_dict = pos.to_dict()
        pos_dict["status"] = "STOP_LOSS_HIT"
        intent2 = _make_intent(intent_id="TI_new_after_close", entry_price=1.14)
        r = simulate_intent_only([intent2], "2026-06-18", existing_positions=[pos_dict])
        assert r.position_count == 2  # existing closed + new
        assert r.lifecycle_stats["positions_skipped_overlap_open"] == 0

    def test_different_timeframe_allowed(self):
        """Different timeframe does not block."""
        r1 = simulate_intent_only([_make_intent()], "2026-06-18")
        intent2 = _make_intent(intent_id="TI_diff_tf", timeframe="1h")
        r2 = simulate_intent_only([intent2], "2026-06-18", existing_positions=r1.positions)
        assert r2.position_count == 2
        assert r2.lifecycle_stats["positions_skipped_overlap_open"] == 0

    def test_different_side_allowed(self):
        """Different side does not block."""
        r1 = simulate_intent_only([_make_intent()], "2026-06-18")
        intent2 = _make_long_intent(intent_id="TI_diff_side")
        r2 = simulate_intent_only([intent2], "2026-06-18", existing_positions=r1.positions)
        assert r2.position_count == 2
        assert r2.lifecycle_stats["positions_skipped_overlap_open"] == 0

    def test_different_strategy_allowed(self):
        """Different strategy_id does not block."""
        r1 = simulate_intent_only([_make_intent()], "2026-06-18")
        intent2 = _make_intent(intent_id="TI_diff_strat", strategy_id="other_strategy")
        r2 = simulate_intent_only([intent2], "2026-06-18", existing_positions=r1.positions)
        assert r2.position_count == 2
        assert r2.lifecycle_stats["positions_skipped_overlap_open"] == 0

    def test_overlap_with_klines(self):
        """Overlap guard works in simulate_with_klines too."""
        r1 = simulate_intent_only([_make_intent()], "2026-06-18")
        intent2 = _make_intent(intent_id="TI_overlap_kl")
        bars_map = {"XRPUSDT_15m": [_make_bar("XRPUSDT", "15m", 1.15, 1.16, 1.13, 1.14, timestamp=9999)]}
        r2 = simulate_with_klines(
            [intent2], bars_map, "2026-06-18",
            existing_positions=r1.positions,
        )
        assert r2.position_count == 1
        assert r2.lifecycle_stats["positions_skipped_overlap_open"] == 1

    def test_overlap_skip_details(self):
        """Skipped overlap intents contain metadata."""
        r1 = simulate_intent_only([_make_intent()], "2026-06-18")
        intent2 = _make_intent(intent_id="TI_detail")
        r2 = simulate_intent_only([intent2], "2026-06-18", existing_positions=r1.positions)
        details = r2.lifecycle_stats["skipped_overlap_intents"]
        assert len(details) == 1
        assert details[0]["intent_id"] == "TI_detail"
        assert details[0]["reason"] == "existing_open_exposure"

    def test_overlap_guard_enabled_flag(self):
        r = simulate_intent_only([], "2026-06-18")
        assert r.lifecycle_stats["overlap_guard_enabled"] is True

    def test_overlap_keys_count(self):
        r1 = simulate_intent_only([_make_intent(), _make_long_intent()], "2026-06-18")
        assert r1.lifecycle_stats["overlap_keys_count"] == 0  # no existing
        r2 = simulate_intent_only([], "2026-06-18", existing_positions=r1.positions)
        assert r2.lifecycle_stats["overlap_keys_count"] == 2


class TestUpdateOnly:
    def test_no_new_positions_created(self):
        """Update-only mode never creates new positions."""
        pos = open_position(_make_intent())
        existing = [pos.to_dict()]
        existing[0]["opened_bar_time"] = 100
        bars = [_make_bar("XRPUSDT", "15m", 1.15, 1.16, 1.13, 1.14, timestamp=200)]
        r = simulate_existing_positions_update_only(
            existing, {"XRPUSDT_15m": bars}, "2026-06-18",
        )
        assert r.lifecycle_stats["new_positions_count"] == 0
        assert r.position_count == 1

    def test_updates_open_position_with_future_tp(self):
        """Update-only can trigger TP on existing OPEN position."""
        pos = open_position(_make_intent())
        pos_dict = pos.to_dict()
        pos_dict["opened_bar_time"] = 100
        bars = [_make_bar("XRPUSDT", "15m", 1.12, 1.13, 1.08, 1.10, timestamp=200)]
        r = simulate_existing_positions_update_only(
            [pos_dict], {"XRPUSDT_15m": bars}, "2026-06-18",
        )
        assert r.positions[0]["status"] == "TAKE_PROFIT_HIT"

    def test_updates_open_position_with_future_sl(self):
        """Update-only can trigger SL on existing OPEN position."""
        pos = open_position(_make_intent())
        pos_dict = pos.to_dict()
        pos_dict["opened_bar_time"] = 100
        bars = [_make_bar("XRPUSDT", "15m", 1.16, 1.19, 1.14, 1.17, timestamp=200)]
        r = simulate_existing_positions_update_only(
            [pos_dict], {"XRPUSDT_15m": bars}, "2026-06-18",
        )
        assert r.positions[0]["status"] == "STOP_LOSS_HIT"

    def test_update_only_ms_opened_time_with_seconds_bar_can_hit_long_tp(self):
        """Persisted ms opened_bar_time works with adapter-style second bars."""
        pos = open_position(_make_long_intent(
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
        ))
        pos_dict = pos.to_dict()
        pos_dict["opened_bar_time"] = 1700000000000
        bars = [_make_bar("BTCUSDT", "15m", 100.0, 111.0, 99.0, 110.5, timestamp=1700000300)]
        r = simulate_existing_positions_update_only(
            [pos_dict], {"BTCUSDT_15m": bars}, "2026-06-18",
        )
        assert r.positions[0]["status"] == "TAKE_PROFIT_HIT"
        assert r.lifecycle_stats["positions_updated_count"] == 1
        assert r.lifecycle_stats["positions_skipped_no_future_bars"] == 0

    def test_update_only_ms_opened_time_with_seconds_bar_can_hit_short_tp(self):
        """Numeric-string ms opened_bar_time works with second bars for shorts."""
        pos = open_position(_make_intent(
            entry_price=100.0,
            stop_loss=105.0,
            take_profit=90.0,
        ))
        pos_dict = pos.to_dict()
        pos_dict["opened_bar_time"] = "1700000000000"
        bars = [_make_bar("XRPUSDT", "15m", 100.0, 101.0, 89.0, 90.5, timestamp=1700000300)]
        r = simulate_existing_positions_update_only(
            [pos_dict], {"XRPUSDT_15m": bars}, "2026-06-18",
        )
        assert r.positions[0]["status"] == "TAKE_PROFIT_HIT"
        assert r.lifecycle_stats["positions_updated_count"] == 1
        assert r.lifecycle_stats["positions_skipped_no_future_bars"] == 0

    def test_keeps_open_if_no_future_bars(self):
        """Update-only keeps OPEN if no future bars available."""
        pos = open_position(_make_intent())
        pos_dict = pos.to_dict()
        pos_dict["opened_bar_time"] = 10000
        bars = [_make_bar("XRPUSDT", "15m", 1.15, 1.16, 1.13, 1.14, timestamp=5000)]
        r = simulate_existing_positions_update_only(
            [pos_dict], {"XRPUSDT_15m": bars}, "2026-06-18",
        )
        assert r.positions[0]["status"] == "OPEN"
        assert r.lifecycle_stats["positions_skipped_no_future_bars"] == 1

    def test_keeps_closed_unchanged(self):
        """Update-only does not modify closed positions."""
        pos = open_position(_make_intent())
        pos_dict = pos.to_dict()
        pos_dict["status"] = "STOP_LOSS_HIT"
        pos_dict["closed_at"] = "2026-01-01"
        bars = [_make_bar("XRPUSDT", "15m", 1.12, 1.13, 1.08, 1.10, timestamp=99999)]
        r = simulate_existing_positions_update_only(
            [pos_dict], {"XRPUSDT_15m": bars}, "2026-06-18",
        )
        assert r.positions[0]["status"] == "STOP_LOSS_HIT"
        assert r.lifecycle_stats["positions_skipped_closed"] == 1

    def test_empty_positions(self):
        r = simulate_existing_positions_update_only([], {}, "2026-06-18")
        assert r.position_count == 0
        assert r.lifecycle_stats["new_positions_count"] == 0
        assert r.lifecycle_stats["update_only"] is True

    def test_mode_is_update_only(self):
        r = simulate_existing_positions_update_only([], {}, "2026-06-18")
        assert r.mode == "update_only"

    def test_skipped_missing_bars(self):
        """Positions without matching bars are counted as skipped_missing_bars."""
        pos = open_position(_make_intent())
        pos_dict = pos.to_dict()
        pos_dict["opened_bar_time"] = 100
        r = simulate_existing_positions_update_only(
            [pos_dict], {}, "2026-06-18",
        )
        assert r.lifecycle_stats["positions_skipped_missing_bars"] == 1


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
