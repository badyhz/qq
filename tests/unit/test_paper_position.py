"""Tests for paper position model — open_position, validation, lifecycle."""
from __future__ import annotations

import json
import os
import py_compile
import tempfile
import datetime as _dt

import pytest

from core.paper_trading.paper_position import (
    open_position, dict_to_position, PaperPosition,
    POSITION_SAFETY_FLAGS, CLOSED_STATUSES,
    load_canonical_positions, filter_canonical_closed_clean,
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


# --- Cumulative accounting tests ---

def _write_ledger_records(path: str, records: list[dict]):
    """Append records to a JSONL ledger file."""
    with open(path, "a") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


def _make_closed(position_id: str, status: str = "TAKE_PROFIT_HIT", **overrides) -> dict:
    now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    rec = {
        "position_id": position_id,
        "strategy_id": "test_strat",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "side": "LONG",
        "status": status,
        "entry_price": 100.0,
        "exit_price": 110.0,
        "stop_loss": 95.0,
        "take_profit": 110.0,
        "r_multiple": 2.0,
        "realized_pnl": 10.0,
        "lifecycle_mode": "future_only",
        "opened_bar_time": 1000,
        "closed_at": now_iso,
        "quarantine_status": "CLEAN",
        "source_mode": "real_public_readonly",
        "recorded_at": now_iso,
    }
    rec.update(overrides)
    return rec


def _make_open(position_id: str, **overrides) -> dict:
    now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    rec = {
        "position_id": position_id,
        "strategy_id": "test_strat",
        "symbol": "ETHUSDT",
        "timeframe": "1h",
        "side": "LONG",
        "status": "OPEN",
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "take_profit": 110.0,
        "r_multiple": 0.0,
        "realized_pnl": 0.0,
        "lifecycle_mode": "future_only",
        "opened_bar_time": 2000,
        "quarantine_status": "CLEAN",
        "source_mode": "real_public_readonly",
        "recorded_at": now_iso,
    }
    rec.update(overrides)
    return rec


class TestCanonicalLoader:
    """Tests for load_canonical_positions and filter_canonical_closed_clean."""

    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result, diag = load_canonical_positions(tmpdir)
            assert result == []
            assert diag["raw_count"] == 0

    def test_append_only_no_loss(self):
        """Append-only ledger: same-day multi-round does not lose CLOSED positions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            # Round 1: open 2 positions
            _write_ledger_records(ledger, [
                _make_open("PP_001"),
                _make_open("PP_002"),
            ])
            # Round 2: PP_001 hits TP, PP_002 still open, new PP_003
            _write_ledger_records(ledger, [
                _make_closed("PP_001", "TAKE_PROFIT_HIT"),
                _make_open("PP_003"),
            ])
            # Round 3: PP_002 hits SL, PP_003 still open
            _write_ledger_records(ledger, [
                _make_closed("PP_002", "STOP_LOSS_HIT"),
            ])

            positions, _diag = load_canonical_positions(tmpdir)
            assert len(positions) == 3
            closed = filter_canonical_closed_clean(positions)
            assert len(closed) == 2
            closed_ids = {p["position_id"] for p in closed}
            assert closed_ids == {"PP_001", "PP_002"}

    def test_cross_day_dedup(self):
        """Same position_id appearing on two days is deduped to latest state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger1 = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            ledger2 = os.path.join(tmpdir, "2026-07-02_paper_position_ledger.jsonl")
            # Day 1: PP_001 is OPEN
            _write_ledger_records(ledger1, [_make_open("PP_001")])
            # Day 2: PP_001 is CLOSED
            _write_ledger_records(ledger2, [_make_closed("PP_001", "STOP_LOSS_HIT")])

            positions, _diag = load_canonical_positions(tmpdir)
            assert len(positions) == 1
            assert positions[0]["status"] == "STOP_LOSS_HIT"

    def test_duplicate_run_stable_count(self):
        """Running the same data twice does not increase canonical count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            records = [
                _make_closed("PP_001", "TAKE_PROFIT_HIT"),
                _make_closed("PP_002", "STOP_LOSS_HIT"),
            ]
            # Write twice (simulating two runs)
            _write_ledger_records(ledger, records)
            _write_ledger_records(ledger, records)

            positions, _diag = load_canonical_positions(tmpdir)
            assert len(positions) == 2
            closed = filter_canonical_closed_clean(positions)
            assert len(closed) == 2

    def test_open_not_in_closed_clean(self):
        """OPEN positions are excluded from closed_clean."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            _write_ledger_records(ledger, [
                _make_closed("PP_closed", "TAKE_PROFIT_HIT"),
                _make_open("PP_open"),
            ])

            positions, _diag = load_canonical_positions(tmpdir)
            closed = filter_canonical_closed_clean(positions)
            assert len(closed) == 1
            assert closed[0]["position_id"] == "PP_closed"

    def test_excluded_not_in_closed_clean(self):
        """EXCLUDED positions are excluded from closed_clean."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            _write_ledger_records(ledger, [
                _make_closed("PP_clean", "TAKE_PROFIT_HIT"),
                _make_closed("PP_excluded", "STOP_LOSS_HIT", quarantine_status="EXCLUDED"),
            ])

            positions, _diag = load_canonical_positions(tmpdir)
            closed = filter_canonical_closed_clean(positions)
            assert len(closed) == 1
            assert closed[0]["position_id"] == "PP_clean"

    def test_invalid_status_not_in_closed_clean(self):
        """INVALID status is not included in closed_clean."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            _write_ledger_records(ledger, [
                _make_closed("PP_invalid", "INVALID"),
                _make_closed("PP_valid", "TIMEOUT_EXIT"),
            ])

            positions, _diag = load_canonical_positions(tmpdir)
            closed = filter_canonical_closed_clean(positions)
            assert len(closed) == 1
            assert closed[0]["position_id"] == "PP_valid"

    def test_missing_exit_price_excluded(self):
        """Positions with missing exit_price are excluded from closed_clean."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            _write_ledger_records(ledger, [
                _make_closed("PP_no_exit", "TAKE_PROFIT_HIT", exit_price=None),
                _make_closed("PP_ok", "TAKE_PROFIT_HIT"),
            ])

            positions, _diag = load_canonical_positions(tmpdir)
            closed = filter_canonical_closed_clean(positions)
            assert len(closed) == 1
            assert closed[0]["position_id"] == "PP_ok"

    def test_non_future_only_excluded(self):
        """Positions without lifecycle_mode=future_only are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            _write_ledger_records(ledger, [
                _make_closed("PP_legacy", "TAKE_PROFIT_HIT", lifecycle_mode="unknown"),
                _make_closed("PP_ok", "TAKE_PROFIT_HIT"),
            ])

            positions, _diag = load_canonical_positions(tmpdir)
            closed = filter_canonical_closed_clean(positions)
            assert len(closed) == 1
            assert closed[0]["position_id"] == "PP_ok"

    def test_sorted_by_position_id(self):
        """Canonical positions are sorted by position_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            _write_ledger_records(ledger, [
                _make_closed("PP_C"),
                _make_closed("PP_A"),
                _make_closed("PP_B"),
            ])

            positions, _diag = load_canonical_positions(tmpdir)
            ids = [p["position_id"] for p in positions]
            assert ids == ["PP_A", "PP_B", "PP_C"]
