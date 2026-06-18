"""Tests for paper position quarantine — legacy tagging, clean summary."""
from __future__ import annotations

import os
import py_compile

import pytest

from core.paper_trading.paper_position_quarantine import (
    quarantine_positions, QuarantineResult, QUARANTINE_SAFETY_FLAGS,
)

MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "..",
                           "core", "paper_trading", "paper_position_quarantine.py")


def _make_clean_position(**overrides):
    pos = {
        "position_id": "PP_clean",
        "intent_id": "TI_clean",
        "symbol": "XRPUSDT",
        "side": "SHORT",
        "status": "OPEN",
        "entry_price": 1.15,
        "stop_loss": 1.18,
        "take_profit": 1.09,
        "lifecycle_mode": "future_only",
        "opened_bar_time": 5000,
        "last_checked_bar_time": 6000,
        "exit_reason": "",
        "realized_pnl": 0.0,
        "r_multiple": 0.0,
        "position_size_preview": 100.0,
    }
    pos.update(overrides)
    return pos


def _make_legacy_position(**overrides):
    pos = {
        "position_id": "PP_legacy",
        "intent_id": "TI_legacy",
        "symbol": "BTCUSDT",
        "side": "LONG",
        "status": "STOP_LOSS_HIT",
        "entry_price": 60000.0,
        "stop_loss": 59000.0,
        "take_profit": 62000.0,
        "lifecycle_mode": None,
        "opened_bar_time": None,
        "last_checked_bar_time": None,
        "exit_reason": "old_backtest_sl",
        "realized_pnl": -50.0,
        "r_multiple": -1.0,
        "position_size_preview": 0.5,
    }
    pos.update(overrides)
    return pos


class TestModuleCompiles:
    def test_compiles(self):
        py_compile.compile(MODULE_PATH, doraise=True)


class TestQuarantineResult:
    def test_result_fields(self):
        result = quarantine_positions([], "2026-06-18", "test.json")
        assert result.date == "2026-06-18"
        assert result.source_file == "test.json"
        assert result.position_count == 0
        assert result.quarantined_count == 0
        assert result.clean_count == 0

    def test_to_dict(self):
        result = quarantine_positions([], "2026-06-18")
        d = result.to_dict()
        assert "date" in d
        assert "positions" in d
        assert "safety_flags" in d

    def test_safety_flags_present(self):
        result = quarantine_positions([], "2026-06-18")
        for flag in ["PAPER_ONLY", "NO_ORDER", "NO_ACCOUNT", "READONLY_METADATA_ONLY"]:
            assert flag in result.safety_flags


class TestCleanPositions:
    def test_clean_position_stays_clean(self):
        pos = _make_clean_position()
        result = quarantine_positions([pos], "2026-06-18")
        assert result.clean_count == 1
        assert result.quarantined_count == 0
        assert result.positions[0]["quarantine_status"] == "CLEAN"
        assert result.positions[0]["excluded_from_performance_stats"] is False

    def test_clean_closed_with_future_only(self):
        pos = _make_clean_position(
            status="TAKE_PROFIT_HIT",
            lifecycle_mode="future_only",
            opened_bar_time=5000,
            last_checked_bar_time=6000,
        )
        result = quarantine_positions([pos], "2026-06-18")
        assert result.clean_count == 1


class TestLegacyDetection:
    def test_missing_lifecycle_mode(self):
        pos = _make_legacy_position(lifecycle_mode=None)
        result = quarantine_positions([pos], "2026-06-18")
        assert result.quarantined_count == 1
        assert "missing_lifecycle_mode" in result.positions[0]["quarantine_reasons"]

    def test_missing_opened_bar_time(self):
        pos = _make_legacy_position(opened_bar_time=None)
        result = quarantine_positions([pos], "2026-06-18")
        assert "missing_opened_bar_time" in result.positions[0]["quarantine_reasons"]

    def test_closed_without_future_only(self):
        pos = _make_legacy_position(
            status="STOP_LOSS_HIT",
            lifecycle_mode="backtest",
        )
        result = quarantine_positions([pos], "2026-06-18")
        assert "closed_without_future_only_lifecycle" in result.positions[0]["quarantine_reasons"]

    def test_same_cycle_update(self):
        pos = _make_legacy_position(
            status="STOP_LOSS_HIT",
            lifecycle_mode="future_only",
            opened_bar_time=5000,
            last_checked_bar_time=5000,
        )
        result = quarantine_positions([pos], "2026-06-18")
        assert "same_cycle_update" in result.positions[0]["quarantine_reasons"]

    def test_legacy_exit_reason_old_backtest(self):
        pos = _make_legacy_position(exit_reason="old_backtest_sl")
        result = quarantine_positions([pos], "2026-06-18")
        assert "legacy_exit_reason_old_backtest" in result.positions[0]["quarantine_reasons"]

    def test_legacy_exit_reason_same_cycle(self):
        pos = _make_legacy_position(exit_reason="same_cycle_exit")
        result = quarantine_positions([pos], "2026-06-18")
        assert "legacy_exit_reason_same_cycle" in result.positions[0]["quarantine_reasons"]

    def test_legacy_exit_reason_unknown(self):
        pos = _make_legacy_position(exit_reason="unknown")
        result = quarantine_positions([pos], "2026-06-18")
        assert "legacy_exit_reason_unknown" in result.positions[0]["quarantine_reasons"]

    def test_multiple_reasons(self):
        pos = _make_legacy_position()  # missing lifecycle, missing opened_bar, old_backtest
        result = quarantine_positions([pos], "2026-06-18")
        reasons = result.positions[0]["quarantine_reasons"]
        assert len(reasons) >= 3

    def test_reason_counts(self):
        pos = _make_legacy_position()
        result = quarantine_positions([pos], "2026-06-18")
        assert result.reason_counts["missing_lifecycle_mode"] == 1


class TestCleanSummary:
    def test_clean_summary_excludes_quarantined(self):
        clean = _make_clean_position(realized_pnl=10.0, r_multiple=2.0)
        legacy = _make_legacy_position(realized_pnl=-50.0, r_multiple=-1.0)
        result = quarantine_positions([clean, legacy], "2026-06-18")
        summary = result.clean_summary
        assert summary["clean_position_count"] == 1
        assert summary["excluded_count"] == 1
        assert summary["clean_total_realized_pnl"] == 10.0

    def test_clean_summary_status_counts(self):
        clean_open = _make_clean_position(status="OPEN")
        clean_tp = _make_clean_position(
            position_id="PP_tp", status="TAKE_PROFIT_HIT",
            realized_pnl=20.0, r_multiple=2.0,
        )
        result = quarantine_positions([clean_open, clean_tp], "2026-06-18")
        summary = result.clean_summary
        assert summary["clean_open_count"] == 1
        assert summary["clean_take_profit_hit_count"] == 1

    def test_clean_avg_r(self):
        p1 = _make_clean_position(position_id="PP1", r_multiple=2.0, realized_pnl=10.0)
        p2 = _make_clean_position(position_id="PP2", r_multiple=-1.0, realized_pnl=-5.0)
        result = quarantine_positions([p1, p2], "2026-06-18")
        assert result.clean_summary["clean_avg_r_multiple"] == 0.5


class TestMixedPositions:
    def test_mixed_count(self):
        positions = [
            _make_clean_position(position_id="PP1"),
            _make_clean_position(position_id="PP2"),
            _make_legacy_position(position_id="PP3"),
            _make_legacy_position(position_id="PP4"),
        ]
        result = quarantine_positions(positions, "2026-06-18")
        assert result.position_count == 4
        assert result.clean_count == 2
        assert result.quarantined_count == 2

    def test_positions_preserved(self):
        positions = [_make_clean_position(), _make_legacy_position()]
        result = quarantine_positions(positions, "2026-06-18")
        assert len(result.positions) == 2


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
