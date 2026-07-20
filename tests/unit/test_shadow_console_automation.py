"""Tests for shadow console automation — input integrity.

Covers:
1. Terminal conflict detection
2. Update-only formal entry
3. Fingerprint & NaN/Inf
4. Six-way count (all mandatory, type-checked)
5. Missing-field matrix
6. Four-way run_id consistency
7. Five-way date consistency
8. Step-level status validation
9. Timeline validation
10. JSON safety (allow_nan=False)
11. HTML injection safety
12. Shell pipeline (real execution)
13. Generator CLI
14. Nginx path contract
15. Release retention (deterministic)
16. Atomic release
17. Formal constructor chain
"""
from __future__ import annotations

import json
import math
import os
import re
import stat
import subprocess
import tempfile
import datetime as _dt
from decimal import Decimal
from pathlib import Path

import pytest

from core.paper_trading.paper_position import (
    select_canonical_position_state,
    PositionSelection,
    position_state_fingerprint,
    load_canonical_positions,
    load_canonical_closed_clean_positions,
    _normalize_fingerprint_value,
    _is_finite_number,
)
from core.paper_trading.paper_performance_metrics import compute_performance
from core.paper_trading.shadow_run_registry import (
    build_run_record,
    ShadowSampleGateResult,
    evaluate_gate,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

_NOW = _dt.datetime.now(_dt.timezone.utc)
NOW_ISO = _NOW.isoformat(timespec="seconds")
_FINISHED = _NOW - _dt.timedelta(minutes=5)
_STARTED = _FINISHED - _dt.timedelta(minutes=30)
_RUN_ID = "test_run_dynamic_001"
_DATE = _FINISHED.date().isoformat()
_STARTED_AT = _STARTED.isoformat(timespec="seconds")
_FINISHED_AT = _FINISHED.isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pos(position_id: str, status: str = "OPEN", **kw) -> dict:
    """Base position record for testing."""
    rec = {
        "position_id": position_id,
        "strategy_id": "test_strat",
        "symbol": "BTC",
        "timeframe": "1h",
        "side": "LONG",
        "status": status,
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "take_profit": 110.0,
        "opened_at": "2026-07-10T10:00:00Z",
        "opened_bar_time": 1752141600000,
        "lifecycle_mode": "future_only",
        "source_mode": "trade_intent",
        "quarantine_status": "CLEAN",
        "date": _DATE,
    }
    if status in ("TAKE_PROFIT_HIT", "STOP_LOSS_HIT", "TIMEOUT_EXIT", "INVALID"):
        rec["exit_price"] = 110.0 if status == "TAKE_PROFIT_HIT" else 95.0
        rec["exit_reason"] = status.lower()
        rec["closed_at"] = "2026-07-10T12:00:00Z"
        rec["r_multiple"] = 1.0 if status == "TAKE_PROFIT_HIT" else -1.0
        rec["realized_pnl"] = 10.0 if status == "TAKE_PROFIT_HIT" else -5.0
    rec.update(kw)
    return rec


def _write(path: str, records: list[dict]):
    with open(path, "a") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _make_steps(status: str = "PASS", exit_code: int = 0,
                started: str = _STARTED_AT, finished: str = _FINISHED_AT) -> list[dict]:
    return [{
        "step_name": "test_step",
        "command": "test",
        "started_at": started,
        "finished_at": finished,
        "duration_seconds": 30,
        "exit_code": exit_code,
        "status": status,
        "stdout_tail": "",
        "stderr_tail": "",
    }]


def _make_lifecycle(date: str = _DATE, status: str = "PASS",
                    steps: list | None = None, run_id: str = _RUN_ID) -> dict:
    return {
        "date": date,
        "mode": "real_public_http",
        "allow_public_http": True,
        "pipeline_status": status,
        "started_at": _STARTED_AT,
        "finished_at": _FINISHED_AT,
        "steps": steps if steps is not None else _make_steps(status),
        "summary": {},
        "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY"],
        "run_id": run_id,
    }


def _make_update(date: str = _DATE, status: str = "PASS",
                 steps: list | None = None, run_id: str = _RUN_ID) -> dict:
    return {
        "date": date,
        "mode": "real_public_http",
        "pipeline_type": "update_only",
        "allow_public_http": True,
        "pipeline_status": status,
        "started_at": _STARTED_AT,
        "finished_at": _FINISHED_AT,
        "steps": steps if steps is not None else _make_steps(status),
        "summary": {},
        "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY"],
        "run_id": run_id,
    }


def _make_scorecard(date: str = _DATE, closed: int = 1,
                    cumulative: int = 1, strategies: list | None = None) -> dict:
    if strategies is None:
        strategies = [{
            "strategy_id": "test_strat",
            "strategy_type": "macd",
            "symbol_count": 1,
            "position_count": closed,
            "open_count": 0,
            "closed_count": closed,
            "tp_count": closed,
            "sl_count": 0,
            "timeout_count": 0,
            "realized_pnl": 10.0,
            "unrealized_pnl": 0.0,
            "avg_r_multiple": 1.0,
            "win_rate": 1.0,
            "profit_factor": 99.0,
            "expectancy_r": 1.0,
            "strategy_score": 1.0,
            "sample_status": "PASS",
            "strategy_status": "PASS",
        }]
    return {
        "date": date,
        "global_metrics": {
            "total_positions": closed,
            "clean_positions": closed,
            "excluded_positions": 0,
            "open_positions": 0,
            "closed_positions": closed,
            "take_profit_hit": closed,
            "stop_loss_hit": 0,
            "timeout_exit": 0,
            "realized_pnl": 10.0,
            "unrealized_pnl": 0.0,
            "avg_r_multiple": 1.0,
            "win_rate": 1.0,
            "loss_rate": 0.0,
            "profit_factor": 99.0,
            "expectancy_r": 1.0,
            "max_single_loss_r": 0.0,
            "max_single_win_r": 1.0,
            "sample_status": "PASS",
        },
        "strategy_scorecards": strategies,
        "clean_position_count": closed,
        "excluded_position_count": 0,
        "cumulative_closed_clean": cumulative,
        "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY"],
    }


def _make_gate(date: str = _DATE, cumulative: int = 1,
               run_id: str = _RUN_ID) -> dict:
    return {
        "date": date,
        "total_runs": 1,
        "latest_run_id": run_id,
        "closed_clean_positions": cumulative,
        "cumulative_closed_clean": cumulative,
        "sample_status": "PASS",
        "testnet_gate_status": "BLOCKED",
        "testnet_gate_reasons": ["shadow_only"],
        "registry_path": "test",
        "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY"],
    }


def _make_registry(date: str = _DATE, cumulative: int = 1,
                   run_id: str = _RUN_ID) -> dict:
    return {
        "run_id": run_id,
        "date": date,
        "started_at": _STARTED_AT,
        "finished_at": _FINISHED_AT,
        "mode": "real_public_http",
        "allow_public_http": True,
        "pipeline_status": "PASS",
        "steps_passed": 4,
        "steps_failed": 0,
        "clean_positions": cumulative,
        "excluded_positions": 0,
        "open_clean_positions": 0,
        "closed_clean_positions": cumulative,
        "cumulative_closed_clean": cumulative,
        "accounting_status": "OK",
        "accounting_error": None,
        "sample_status": "PASS",
        "testnet_gate_status": "BLOCKED",
        "testnet_gate_reasons": ["shadow_only"],
        "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY"],
    }


def _write_full_report(report_dir: str, pos: dict, date: str = _DATE,
                       cumulative: int = 1, lc_status: str = "PASS",
                       update_status: str = "PASS", run_id: str = _RUN_ID):
    """Create all report files with production schemas."""
    ledger = os.path.join(report_dir, f"{date}_paper_position_ledger.jsonl")
    _write(ledger, [pos])

    with open(os.path.join(report_dir, f"{date}_paper_performance_scorecard.json"), "w") as f:
        json.dump(_make_scorecard(date, closed=1, cumulative=cumulative), f)
    with open(os.path.join(report_dir, f"{date}_shadow_sample_gate.json"), "w") as f:
        json.dump(_make_gate(date, cumulative=cumulative, run_id=run_id), f)
    with open(os.path.join(report_dir, f"{date}_shadow_lifecycle_result.json"), "w") as f:
        json.dump(_make_lifecycle(date, lc_status, run_id=run_id), f)
    with open(os.path.join(report_dir, f"{date}_shadow_position_update_result.json"), "w") as f:
        json.dump(_make_update(date, update_status, run_id=run_id), f)
    with open(os.path.join(report_dir, f"{date}_shadow_run_registry.jsonl"), "a") as f:
        f.write(json.dumps(_make_registry(date, cumulative, run_id=run_id)) + "\n")


# ===========================================================================
# 1. Terminal conflict detection
# ===========================================================================

class TestTerminalConflict:
    def test_take_profit_vs_stop_loss_conflict(self):
        old = _pos("PP_001", "TAKE_PROFIT_HIT")
        new = _pos("PP_001", "STOP_LOSS_HIT")
        sel = select_canonical_position_state(old, new)
        assert sel.conflict is True
        assert sel.decision == "conflict_terminal"
        assert sel.selected["status"] == "TAKE_PROFIT_HIT"

    def test_same_terminal_field_change_conflict(self):
        old = _pos("PP_001", "TAKE_PROFIT_HIT", r_multiple=1.0)
        new = _pos("PP_001", "TAKE_PROFIT_HIT", r_multiple=2.0)
        sel = select_canonical_position_state(old, new)
        assert sel.conflict is True
        assert sel.conflict_reason == "terminal_field_change"
        assert sel.selected["r_multiple"] == 1.0

    def test_closed_to_open_regression(self):
        old = _pos("PP_001", "TAKE_PROFIT_HIT")
        new = _pos("PP_001", "OPEN")
        sel = select_canonical_position_state(old, new)
        assert sel.conflict is True
        assert sel.conflict_reason == "terminal_irreversible"

    def test_conflict_goes_to_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-10_paper_position_ledger.jsonl")
            _write(ledger, [_pos("PP_001", "TAKE_PROFIT_HIT")])
            _write(ledger, [_pos("PP_001", "STOP_LOSS_HIT")])
            positions, diag = load_canonical_positions(tmpdir)
            assert diag["terminal_conflict_count"] == 1
            assert diag["terminal_conflicts"][0]["conflict_type"] == "terminal_status_conflict"

    def test_field_change_in_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-10_paper_position_ledger.jsonl")
            _write(ledger, [_pos("PP_001", "TAKE_PROFIT_HIT", r_multiple=1.0)])
            _write(ledger, [_pos("PP_001", "TAKE_PROFIT_HIT", r_multiple=2.0)])
            positions, diag = load_canonical_positions(tmpdir)
            assert diag["terminal_conflict_count"] == 1
            assert diag["terminal_conflicts"][0]["conflict_type"] == "terminal_field_change"
            assert diag["terminal_conflicts"][0]["fatal"] is True

    def test_regression_in_diagnostics_nonfatal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-10_paper_position_ledger.jsonl")
            _write(ledger, [_pos("PP_001", "TAKE_PROFIT_HIT")])
            _write(ledger, [_pos("PP_001", "OPEN")])
            positions, diag = load_canonical_positions(tmpdir)
            assert diag["terminal_conflict_count"] == 1
            assert diag["terminal_conflicts"][0]["conflict_type"] == "terminal_regression"
            assert diag["terminal_conflicts"][0]["fatal"] is False

    def test_conflict_goes_to_fatal_errors(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-10_paper_position_ledger.jsonl")
            _write(ledger, [_pos("PP_001", "TAKE_PROFIT_HIT")])
            _write(ledger, [_pos("PP_001", "STOP_LOSS_HIT")])
            eligible, all_pos, diag = load_canonical_closed_clean_positions(tmpdir)
            assert diag["accounting_status"] == "ERROR"

    def test_field_change_fatal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-10_paper_position_ledger.jsonl")
            _write(ledger, [_pos("PP_001", "TAKE_PROFIT_HIT", r_multiple=1.0)])
            _write(ledger, [_pos("PP_001", "TAKE_PROFIT_HIT", r_multiple=2.0)])
            eligible, all_pos, diag = load_canonical_closed_clean_positions(tmpdir)
            assert diag["accounting_status"] == "ERROR"

    def test_regression_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-10_paper_position_ledger.jsonl")
            _write(ledger, [_pos("PP_001", "TAKE_PROFIT_HIT")])
            _write(ledger, [_pos("PP_001", "OPEN")])
            eligible, all_pos, diag = load_canonical_closed_clean_positions(tmpdir)
            assert diag["accounting_status"] == "OK"
            assert len(diag["terminal_regressions"]) == 1


# ===========================================================================
# 2. Update-only formal entry
# ===========================================================================

class TestUpdateOnlyFormalEntry:
    def test_ledger_closed_not_reopened(self):
        from scripts.run_paper_position_simulator import _load_update_existing_positions
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-10_paper_position_ledger.jsonl")
            _write(ledger, [_pos("PP_001", "TAKE_PROFIT_HIT")])
            pos_path = os.path.join(tmpdir, "2026-07-10_paper_positions.json")
            open_pos = _pos("PP_001", "OPEN")
            open_pos["recorded_at"] = "2026-07-10T15:00:00Z"
            with open(pos_path, "w") as f:
                json.dump({"positions": [open_pos]}, f)
            result = _load_update_existing_positions(tmpdir, "2026-07-10")
            assert len(result) == 0

    def test_different_terminal_conflict_aborts(self):
        from scripts.run_paper_position_simulator import _load_update_existing_positions
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-10_paper_position_ledger.jsonl")
            _write(ledger, [_pos("PP_001", "TAKE_PROFIT_HIT")])
            pos_path = os.path.join(tmpdir, "2026-07-10_paper_positions.json")
            with open(pos_path, "w") as f:
                json.dump({"positions": [_pos("PP_001", "STOP_LOSS_HIT")]}, f)
            with pytest.raises(RuntimeError, match="Terminal state conflicts"):
                _load_update_existing_positions(tmpdir, "2026-07-10")


# ===========================================================================
# 3. Fingerprint & NaN/Inf
# ===========================================================================

class TestFingerprint:
    def test_numeric_normalization(self):
        assert _normalize_fingerprint_value(100) == "100"
        assert _normalize_fingerprint_value(100.0) == "100"
        assert _normalize_fingerprint_value(100.00) == "100"

    def test_negative_zero(self):
        assert _normalize_fingerprint_value(-0.0) == "0"
        assert _normalize_fingerprint_value(0) == "0"
        assert _normalize_fingerprint_value(0.0) == "0"

    def test_nan_fingerprint(self):
        result = _normalize_fingerprint_value(float("nan"))
        assert result == "NON_FINITE_NAN"

    def test_positive_inf_fingerprint(self):
        assert _normalize_fingerprint_value(float("inf")) == "NON_FINITE_POS_INF"

    def test_negative_inf_fingerprint(self):
        assert _normalize_fingerprint_value(float("-inf")) == "NON_FINITE_NEG_INF"

    def test_decimal_nan(self):
        assert _normalize_fingerprint_value(Decimal("NaN")) == "NON_FINITE_NAN"

    def test_decimal_inf(self):
        assert _normalize_fingerprint_value(Decimal("Infinity")) == "NON_FINITE_POS_INF"

    def test_is_finite_number(self):
        assert _is_finite_number(100) is True
        assert _is_finite_number(100.0) is True
        assert _is_finite_number(float("nan")) is False
        assert _is_finite_number(float("inf")) is False
        assert _is_finite_number(float("-inf")) is False
        assert _is_finite_number("abc") is False
        assert _is_finite_number(None) is False
        assert _is_finite_number(Decimal("NaN")) is False

    def test_non_finite_rejected_by_accounting(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pos = _pos("PP_001", "TAKE_PROFIT_HIT")
            pos["exit_price"] = float("nan")
            ledger = os.path.join(tmpdir, f"{_DATE}_paper_position_ledger.jsonl")
            _write(ledger, [pos])
            with open(os.path.join(tmpdir, f"{_DATE}_shadow_lifecycle_result.json"), "w") as f:
                json.dump({"date": _DATE, "mode": "real_public_readonly",
                           "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY"],
                           "allow_public_http": True}, f)
            eligible, all_pos, diag = load_canonical_closed_clean_positions(tmpdir)
            assert diag["accounting_status"] == "ERROR"
            assert any("Non-finite" in e for e in diag["fatal_errors"])

    def test_inf_rejected_by_accounting(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pos = _pos("PP_001", "TAKE_PROFIT_HIT")
            pos["r_multiple"] = float("inf")
            ledger = os.path.join(tmpdir, f"{_DATE}_paper_position_ledger.jsonl")
            _write(ledger, [pos])
            with open(os.path.join(tmpdir, f"{_DATE}_shadow_lifecycle_result.json"), "w") as f:
                json.dump({"date": _DATE, "mode": "real_public_readonly",
                           "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY"],
                           "allow_public_http": True}, f)
            eligible, all_pos, diag = load_canonical_closed_clean_positions(tmpdir)
            assert diag["accounting_status"] == "ERROR"

    def test_fingerprint_stability(self):
        pos1 = _pos("PP_001", "OPEN", entry_price=100)
        pos2 = _pos("PP_001", "OPEN", entry_price=100.0)
        assert position_state_fingerprint(pos1) == position_state_fingerprint(pos2)

    def test_observation_change_stable(self):
        pos = _pos("PP_001", "OPEN")
        fp1 = position_state_fingerprint(pos)
        pos["last_checked_at"] = "2026-07-10T13:00:00Z"
        pos["recorded_at"] = "2026-07-10T13:00:00Z"
        assert position_state_fingerprint(pos) == fp1


# ===========================================================================
# 4. Six-way count (all mandatory)
# ===========================================================================

class TestSixWayCount:
    def test_all_six_match(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            bundle, errors = validate_inputs(rd)
            assert errors == []
            c = bundle["counts"]
            assert c["canonical"] == c["scorecard_global"] == c["scorecard_strategy_sum"]
            assert c["canonical"] == c["scorecard_cumulative"] == c["gate_cumulative"]
            assert c["canonical"] == c["registry_cumulative"]

    def test_count_mismatch_fails(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            sc_path = os.path.join(rd, f"{_DATE}_paper_performance_scorecard.json")
            sc = _make_scorecard(cumulative=99)
            with open(sc_path, "w") as f:
                json.dump(sc, f)
            _, errors = validate_inputs(rd)
            assert any("Count mismatch" in e for e in errors)


# ===========================================================================
# 5. Missing-field matrix
# ===========================================================================

class TestMissingFieldMatrix:
    """Each test removes one required field and verifies rejection."""

    def _base_report(self, rd):
        _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))

    def _corrupt_json(self, rd, suffix, mutator):
        path = os.path.join(rd, f"{_DATE}{suffix}")
        data = json.loads(open(path).read())
        mutator(data)
        with open(path, "w") as f:
            json.dump(data, f)

    def _corrupt_registry(self, rd, mutator):
        path = os.path.join(rd, f"{_DATE}_shadow_run_registry.jsonl")
        lines = open(path).read().strip().split("\n")
        rec = json.loads(lines[0])
        mutator(rec)
        with open(path, "w") as f:
            f.write(json.dumps(rec) + "\n")

    def test_missing_sc_global_closed_positions(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            self._base_report(rd)
            self._corrupt_json(rd, "_paper_performance_scorecard.json",
                               lambda d: d["global_metrics"].pop("closed_positions"))
            _, errors = validate_inputs(rd)
            assert any("closed_positions" in e for e in errors)

    def test_missing_sc_strategy_closed_count(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            self._base_report(rd)
            self._corrupt_json(rd, "_paper_performance_scorecard.json",
                               lambda d: d["strategy_scorecards"][0].pop("closed_count"))
            _, errors = validate_inputs(rd)
            assert any("closed_count" in e for e in errors)

    def test_missing_sc_cumulative(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            self._base_report(rd)
            self._corrupt_json(rd, "_paper_performance_scorecard.json",
                               lambda d: d.pop("cumulative_closed_clean"))
            _, errors = validate_inputs(rd)
            assert any("cumulative_closed_clean" in e for e in errors)

    def test_missing_gate_cumulative(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            self._base_report(rd)
            self._corrupt_json(rd, "_shadow_sample_gate.json",
                               lambda d: d.pop("cumulative_closed_clean"))
            _, errors = validate_inputs(rd)
            assert any("cumulative_closed_clean" in e for e in errors)

    def test_missing_registry_cumulative(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            self._base_report(rd)
            self._corrupt_registry(rd, lambda d: d.pop("cumulative_closed_clean"))
            _, errors = validate_inputs(rd)
            assert any("cumulative_closed_clean" in e for e in errors)

    def test_missing_lifecycle_run_id(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            self._base_report(rd)
            self._corrupt_json(rd, "_shadow_lifecycle_result.json",
                               lambda d: d.pop("run_id"))
            _, errors = validate_inputs(rd)
            assert any("run_id" in e.lower() or "Run ID" in e for e in errors)

    def test_missing_update_run_id(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            self._base_report(rd)
            self._corrupt_json(rd, "_shadow_position_update_result.json",
                               lambda d: d.pop("run_id"))
            _, errors = validate_inputs(rd)
            assert any("run_id" in e.lower() or "Run ID" in e for e in errors)

    def test_missing_gate_latest_run_id(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            self._base_report(rd)
            self._corrupt_json(rd, "_shadow_sample_gate.json",
                               lambda d: d.pop("latest_run_id"))
            _, errors = validate_inputs(rd)
            assert any("run_id" in e.lower() or "Run ID" in e for e in errors)

    def test_missing_registry_run_id(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            self._base_report(rd)
            self._corrupt_registry(rd, lambda d: d.pop("run_id"))
            _, errors = validate_inputs(rd)
            assert any("run_id" in e.lower() or "Registry" in e for e in errors)

    def test_sc_global_closed_is_float(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            self._base_report(rd)
            self._corrupt_json(rd, "_paper_performance_scorecard.json",
                               lambda d: d["global_metrics"].__setitem__("closed_positions", 1.5))
            _, errors = validate_inputs(rd)
            assert any("float" in e for e in errors)

    def test_sc_cumulative_is_bool(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            self._base_report(rd)
            self._corrupt_json(rd, "_paper_performance_scorecard.json",
                               lambda d: d.__setitem__("cumulative_closed_clean", True))
            _, errors = validate_inputs(rd)
            assert any("bool" in e for e in errors)

    def test_sc_cumulative_is_negative(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            self._base_report(rd)
            self._corrupt_json(rd, "_paper_performance_scorecard.json",
                               lambda d: d.__setitem__("cumulative_closed_clean", -1))
            _, errors = validate_inputs(rd)
            assert any("negative" in e for e in errors)


# ===========================================================================
# 6. Four-way run_id consistency
# ===========================================================================

class TestRunIdConsistency:
    def test_all_four_match(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            _, errors = validate_inputs(rd)
            assert not any("Run ID" in e for e in errors)

    def test_update_run_id_mismatch(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            self._corrupt(rd, "_shadow_position_update_result.json",
                          lambda d: d.__setitem__("run_id", "WRONG"))
            _, errors = validate_inputs(rd)
            assert any("Run ID" in e for e in errors)

    def test_gate_run_id_mismatch(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            self._corrupt(rd, "_shadow_sample_gate.json",
                          lambda d: d.__setitem__("latest_run_id", "WRONG"))
            _, errors = validate_inputs(rd)
            assert any("Run ID" in e for e in errors)

    def test_duplicate_registry_run_id(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            # Append duplicate registry record
            reg_path = os.path.join(rd, f"{_DATE}_shadow_run_registry.jsonl")
            with open(reg_path, "a") as f:
                f.write(json.dumps(_make_registry()) + "\n")
            _, errors = validate_inputs(rd)
            assert any("2 records" in e for e in errors)

    def _corrupt(self, rd, suffix, mutator):
        path = os.path.join(rd, f"{_DATE}{suffix}")
        data = json.loads(open(path).read())
        mutator(data)
        with open(path, "w") as f:
            json.dump(data, f)


# ===========================================================================
# 7. Five-way date consistency
# ===========================================================================

class TestDateConsistency:
    def test_all_five_match(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            _, errors = validate_inputs(rd)
            assert not any("Date mismatch" in e for e in errors)

    def test_authoritative_date_selects_exact_artifacts(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            with open(os.path.join(rd, "2099-01-01_shadow_lifecycle_result.json"), "w") as f:
                json.dump({"date": "2099-01-01", "pipeline_status": "FAIL"}, f)
            bundle, errors = validate_inputs(rd, report_date=_DATE)
            assert errors == []
            assert bundle["run_date"] == _DATE

    def test_authoritative_date_conflict_is_rejected(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            _, errors = validate_inputs(rd, report_date="2099-01-01")
            assert errors
            assert any("Missing lifecycle" in error for error in errors)

    def test_utc_run_id_does_not_override_report_date(self):
        from scripts.generate_static_console import generate_console, validate_inputs
        with tempfile.TemporaryDirectory() as rd, tempfile.TemporaryDirectory() as od:
            utc_run_id = "20260720T181030Z_shadow_lifecycle"
            _write_full_report(
                rd,
                _pos("PP_001", "TAKE_PROFIT_HIT"),
                run_id=utc_run_id,
            )
            result = generate_console(rd, od, report_date=_DATE)
            assert result["success"] is True
            bundle, errors = validate_inputs(rd, report_date=_DATE)
            assert errors == []
            assert bundle["run_id"] == utc_run_id
            with open(os.path.join(od, "current", "console_data.json")) as f:
                public = json.load(f)
            assert public["run_date"] == _DATE

    def test_gate_date_mismatch(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            gate_path = os.path.join(rd, f"{_DATE}_shadow_sample_gate.json")
            data = json.loads(open(gate_path).read())
            data["date"] = "2099-01-01"
            with open(gate_path, "w") as f:
                json.dump(data, f)
            _, errors = validate_inputs(rd)
            assert any("Date mismatch" in e for e in errors)

    def test_registry_date_mismatch(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            reg_path = os.path.join(rd, f"{_DATE}_shadow_run_registry.jsonl")
            rec = json.loads(open(reg_path).read().strip())
            rec["date"] = "2099-01-01"
            with open(reg_path, "w") as f:
                f.write(json.dumps(rec) + "\n")
            _, errors = validate_inputs(rd)
            assert any("Date mismatch" in e for e in errors)


# ===========================================================================
# 8. Step-level status validation
# ===========================================================================

class TestStepValidation:
    def test_lifecycle_step_fail_blocks(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            lc_path = os.path.join(rd, f"{_DATE}_shadow_lifecycle_result.json")
            data = _make_lifecycle(steps=_make_steps("FAIL"))
            with open(lc_path, "w") as f:
                json.dump(data, f)
            _, errors = validate_inputs(rd)
            assert any("step" in e.lower() and "PASS" in e for e in errors)

    def test_lifecycle_nonzero_exit_blocks(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            lc_path = os.path.join(rd, f"{_DATE}_shadow_lifecycle_result.json")
            data = _make_lifecycle(steps=_make_steps("PASS", exit_code=7))
            with open(lc_path, "w") as f:
                json.dump(data, f)
            _, errors = validate_inputs(rd)
            assert any("exit_code" in e and "7" in e for e in errors)

    def test_update_step_fail_blocks(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            up_path = os.path.join(rd, f"{_DATE}_shadow_position_update_result.json")
            data = _make_update(steps=_make_steps("FAIL"))
            with open(up_path, "w") as f:
                json.dump(data, f)
            _, errors = validate_inputs(rd)
            assert any("step" in e.lower() and "PASS" in e for e in errors)

    def test_update_nonzero_exit_blocks(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            up_path = os.path.join(rd, f"{_DATE}_shadow_position_update_result.json")
            data = _make_update(steps=_make_steps("PASS", exit_code=9))
            with open(up_path, "w") as f:
                json.dump(data, f)
            _, errors = validate_inputs(rd)
            assert any("exit_code" in e and "9" in e for e in errors)

    def test_empty_steps_blocks(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            lc_path = os.path.join(rd, f"{_DATE}_shadow_lifecycle_result.json")
            data = _make_lifecycle(steps=[])
            with open(lc_path, "w") as f:
                json.dump(data, f)
            _, errors = validate_inputs(rd)
            assert any("steps" in e.lower() and "empty" in e.lower() for e in errors)

    def test_missing_step_started_at_blocks(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            lc_path = os.path.join(rd, f"{_DATE}_shadow_lifecycle_result.json")
            steps = _make_steps()
            del steps[0]["started_at"]
            data = _make_lifecycle(steps=steps)
            with open(lc_path, "w") as f:
                json.dump(data, f)
            _, errors = validate_inputs(rd)
            assert any("started_at" in e for e in errors)


# ===========================================================================
# 9. Timeline validation
# ===========================================================================

class TestTimelineValidation:
    def test_started_after_finished_blocks(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            lc_path = os.path.join(rd, f"{_DATE}_shadow_lifecycle_result.json")
            data = _make_lifecycle(steps=_make_steps(
                started=_FINISHED_AT, finished=_STARTED_AT,
            ))
            with open(lc_path, "w") as f:
                json.dump(data, f)
            _, errors = validate_inputs(rd)
            assert any("started_at" in e and "finished_at" in e for e in errors)

    def test_registry_before_lifecycle_blocks(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            reg_path = os.path.join(rd, f"{_DATE}_shadow_run_registry.jsonl")
            rec = json.loads(open(reg_path).read().strip())
            # Registry finished before lifecycle finished
            rec["finished_at"] = "2026-07-13T21:00:00+08:00"
            with open(reg_path, "w") as f:
                f.write(json.dumps(rec) + "\n")
            _, errors = validate_inputs(rd)
            assert any("Timeline" in e and "Registry" in e for e in errors)

    def test_date_only_rejected(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            reg_path = os.path.join(rd, f"{_DATE}_shadow_run_registry.jsonl")
            rec = json.loads(open(reg_path).read().strip())
            rec["finished_at"] = "2026-07-13"
            with open(reg_path, "w") as f:
                f.write(json.dumps(rec) + "\n")
            _, errors = validate_inputs(rd)
            assert any("finished_at" in e.lower() or "invalid" in e.lower() for e in errors)

    def test_future_time_rejected(self):
        """Far-future timestamps fail closed."""
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            reg_path = os.path.join(rd, f"{_DATE}_shadow_run_registry.jsonl")
            rec = json.loads(open(reg_path).read().strip())
            rec["finished_at"] = "2099-12-31T23:59:59+00:00"
            with open(reg_path, "w") as f:
                f.write(json.dumps(rec) + "\n")
            _, errors = validate_inputs(rd)
            assert any("future" in e.lower() for e in errors)


# ===========================================================================
# 10. JSON safety (allow_nan=False)
# ===========================================================================

class TestJsonSafety:
    def test_nan_in_scorecard_blocks(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd:
            with tempfile.TemporaryDirectory() as od:
                _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
                sc_path = os.path.join(rd, f"{_DATE}_paper_performance_scorecard.json")
                sc = _make_scorecard()
                # NaN in strategy win_rate reaches build_public_json → json.dumps(allow_nan=False)
                sc["strategy_scorecards"][0]["win_rate"] = float("nan")
                with open(sc_path, "w") as f:
                    json.dump(sc, f)
                result = generate_console(rd, od)
                assert result["success"] is False

    def test_inf_in_position_blocks(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd:
            with tempfile.TemporaryDirectory() as od:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT", r_multiple=float("inf"))
                _write_full_report(rd, pos)
                result = generate_console(rd, od)
                assert result["success"] is False


# ===========================================================================
# 11. HTML injection safety
# ===========================================================================

class TestHtmlSafety:
    def test_symbol_injection_escaped(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd:
            with tempfile.TemporaryDirectory() as od:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT",
                           symbol='<img src=x onerror=alert(1)>')
                _write_full_report(rd, pos)
                result = generate_console(rd, od)
                assert result["success"] is True
                for fname in ["index.html", "index_en.html"]:
                    content = open(os.path.join(od, "current", fname)).read()
                    assert "<img" not in content
                    assert "&lt;img" in content

    def test_strategy_injection_escaped(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd:
            with tempfile.TemporaryDirectory() as od:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT",
                           strategy_id='<script>alert(1)</script>')
                _write_full_report(rd, pos)
                result = generate_console(rd, od)
                assert result["success"] is True
                for fname in ["index.html", "index_en.html"]:
                    content = open(os.path.join(od, "current", fname)).read()
                    assert "<script>" not in content
                    assert "&lt;script&gt;" in content

    def test_exit_reason_injection_escaped(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd:
            with tempfile.TemporaryDirectory() as od:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT",
                           exit_reason='</td><script>alert(1)</script>')
                _write_full_report(rd, pos)
                result = generate_console(rd, od)
                assert result["success"] is True
                for fname in ["index.html", "index_en.html"]:
                    content = open(os.path.join(od, "current", fname)).read()
                    assert "<script>" not in content

    def test_no_javascript_href(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd:
            with tempfile.TemporaryDirectory() as od:
                _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
                result = generate_console(rd, od)
                assert result["success"] is True
                for fname in ["index.html", "index_en.html"]:
                    content = open(os.path.join(od, "current", fname)).read()
                    assert "javascript:" not in content


# ===========================================================================
# 12. Shell pipeline (real execution)
# ===========================================================================

class TestShellPipeline:
    def test_syntax_valid(self):
        result = subprocess.run(
            ["bash", "-n", "scripts/run_cloud_shadow_collection_once.sh"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0

    def test_main_guard_exists(self):
        content = open(str(REPO_ROOT / "scripts" / "run_cloud_shadow_collection_once.sh")).read()
        assert 'BASH_SOURCE[0]' in content
        assert 'main "$@"' in content

    def test_run_step_captures_real_exit(self):
        """Actually source the script and run run_step with a failing command."""
        script = str(REPO_ROOT / "scripts" / "run_cloud_shadow_collection_once.sh")
        result = subprocess.run(
            ["bash", "-c", f"source {script}; run_step TestCmd bash -c 'exit 7'"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 7
        assert "FAILED (exit=7)" in result.stdout

    def test_run_step_returns_zero_on_success(self):
        script = str(REPO_ROOT / "scripts" / "run_cloud_shadow_collection_once.sh")
        result = subprocess.run(
            ["bash", "-c", f"source {script}; run_step TestCmd true"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0

    def test_cloud_wrapper_uses_one_shared_batch_id_in_formal_order(self):
        content = open(str(REPO_ROOT / "scripts" / "run_cloud_shadow_collection_once.sh")).read()
        assert content.count("build_pipeline_context()") == 1
        # Lifecycle, Update, Scorecard, Registry, Gate, and the optional
        # post-activation Scorecard all consume the same authoritative date.
        assert content.count('--date "$REPORT_DATE"') == 6
        assert '--report-date "$REPORT_DATE"' in content
        assert content.count('--run-id "$BATCH_RUN_ID"') == 3
        assert "--defer-registry" in content
        lifecycle = content.index('run_step "Lifecycle"')
        update = content.index('run_step "Update-Only"')
        scorecard = content.index('run_step "Scorecard"')
        registry = content.index('run_step "Final Registry"')
        gate = content.index('run_step "Gate"')
        console = content.index('echo "=== Static Console ==="')
        post = content.index('echo "=== Post Status ==="')
        assert lifecycle < update < scorecard < registry < gate < console < post

    def test_cloud_wrapper_defers_provisional_outputs(self):
        content = open(str(REPO_ROOT / "scripts" / "run_cloud_shadow_collection_once.sh")).read()
        lifecycle_block = content[content.index('run_step "Lifecycle"'):
                                  content.index('run_step "Update-Only"')]
        update_block = content[content.index('run_step "Update-Only"'):
                               content.index('run_step "Scorecard"')]
        assert "--defer-scorecard" in lifecycle_block
        assert "--defer-registry" in lifecycle_block
        assert "--defer-scorecard" in update_block
        assert "--defer-gate" in update_block
        assert "--defer-registry" in update_block

    def test_update_failure_writes_no_registry_and_stops_downstream(self, tmp_path):
        project = tmp_path / "project"
        fakebin = project / "fakebin"
        (project / ".venv" / "bin").mkdir(parents=True)
        (project / "logs" / "cloud_shadow").mkdir(parents=True)
        fakebin.mkdir()
        activate = project / ".venv" / "bin" / "activate"
        activate.write_text(f'export PATH="{fakebin}:$PATH"\n')
        call_log = tmp_path / "calls.log"

        fake_python = fakebin / "python3"
        fake_python.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$*\" >> \"$CALL_LOG\"\n"
            "if [ \"${1:-}\" = '-c' ]; then\n"
            "  echo 'RUN-123 2026-07-13T00:00:00+00:00 2026-07-13'\n"
            "elif [[ \"$*\" == *run_shadow_position_update_only.py* ]]; then\n"
            "  exit 23\n"
            "fi\n"
        )
        fake_python.chmod(0o755)
        fake_git = fakebin / "git"
        fake_git.write_text(
            "#!/usr/bin/env bash\n"
            "echo 8164e8f1a4352f4d0884378869881d6c76cebda1\n"
        )
        fake_git.chmod(0o755)

        env = os.environ.copy()
        env.update({"PROJECT_DIR": str(project), "CALL_LOG": str(call_log)})
        result = subprocess.run(
            ["bash", str(REPO_ROOT / "scripts" / "run_cloud_shadow_collection_once.sh")],
            capture_output=True, text=True, env=env,
        )
        assert result.returncode == 23
        calls = call_log.read_text()
        assert "run_shadow_trading_lifecycle.py" in calls
        assert "run_shadow_position_update_only.py" in calls
        assert "run_paper_performance_scorecard.py" not in calls
        assert "--finalize-registry" not in calls
        assert "run_sample_collection_gate.py" not in calls
        assert "generate_static_console.py" not in calls


# ===========================================================================
# 13. Generator CLI
# ===========================================================================

class TestGeneratorCLI:
    def test_cli_success(self):
        with tempfile.TemporaryDirectory() as rd:
            with tempfile.TemporaryDirectory() as od:
                _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
                result = subprocess.run(
                    ["python3", "scripts/generate_static_console.py",
                     "--report-dir", rd, "--output-dir", od,
                     "--server-commit", "abc1234"],
                    capture_output=True, text=True, cwd=str(REPO_ROOT),
                )
                assert result.returncode == 0
                assert "version=" in result.stdout
                assert "public_root:" in result.stdout

    def test_cli_invalid_commit_rejected(self):
        with tempfile.TemporaryDirectory() as rd:
            with tempfile.TemporaryDirectory() as od:
                result = subprocess.run(
                    ["python3", "scripts/generate_static_console.py",
                     "--report-dir", rd, "--output-dir", od,
                     "--server-commit", "not-a-hash!"],
                    capture_output=True, text=True, cwd=str(REPO_ROOT),
                )
                assert result.returncode == 1

    def test_cli_lifecycle_fail_blocks(self):
        with tempfile.TemporaryDirectory() as rd:
            with tempfile.TemporaryDirectory() as od:
                _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"), lc_status="FAIL")
                result = subprocess.run(
                    ["python3", "scripts/generate_static_console.py",
                     "--report-dir", rd, "--output-dir", od],
                    capture_output=True, text=True, cwd=str(REPO_ROOT),
                )
                assert result.returncode == 1


# ===========================================================================
# 14. Nginx path contract
# ===========================================================================

class TestNginxPathContract:
    def test_no_root_level_files(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd:
            with tempfile.TemporaryDirectory() as od:
                _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
                result = generate_console(rd, od)
                assert result["success"] is True
                assert not os.path.isfile(os.path.join(od, "index.html"))
                assert os.path.isfile(os.path.join(od, "current", "index.html"))

    def test_current_is_symlink(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd:
            with tempfile.TemporaryDirectory() as od:
                _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
                result = generate_console(rd, od)
                assert result["success"] is True
                assert os.path.islink(os.path.join(od, "current"))
                assert result["public_root"].endswith("/current")
                assert result["required_nginx_alias"].endswith("/current/")


# ===========================================================================
# 15. Release retention (deterministic)
# ===========================================================================

class TestReleaseRetention:
    def test_max_releases_kept(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd:
            with tempfile.TemporaryDirectory() as od:
                _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
                for _ in range(8):
                    result = generate_console(rd, od)
                    assert result["success"] is True

                releases_dir = os.path.join(od, "releases")
                remaining = [
                    d for d in os.listdir(releases_dir)
                    if os.path.isdir(os.path.join(releases_dir, d))
                    and re.match(r"^\d{8}-\d{6}-[0-9a-f]{8}$", d)
                ]
                assert len(remaining) <= 5

    def test_current_not_deleted(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd:
            with tempfile.TemporaryDirectory() as od:
                _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
                for _ in range(8):
                    generate_console(rd, od)

                current = os.path.join(od, "current")
                assert os.path.islink(current)
                target = os.readlink(current)
                assert os.path.isdir(os.path.join(od, target))

    def test_current_always_in_keep_set(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd:
            with tempfile.TemporaryDirectory() as od:
                _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
                results = []
                for _ in range(10):
                    r = generate_console(rd, od)
                    results.append(r)

                # The last current target must still exist
                last_target = results[-1]["current_target"]
                assert os.path.isdir(os.path.join(od, last_target))


# ===========================================================================
# 16. Atomic release
# ===========================================================================

class TestAtomicRelease:
    def test_symlink_switch(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd:
            with tempfile.TemporaryDirectory() as od:
                _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
                r1 = generate_console(rd, od)
                assert r1["success"] is True
                v1 = r1["version_id"]
                current = os.path.join(od, "current")
                assert os.readlink(current) == f"releases/{v1}"
                r2 = generate_console(rd, od)
                assert r2["success"] is True
                v2 = r2["version_id"]
                assert v2 != v1
                assert os.readlink(current) == f"releases/{v2}"


class TestPublicReleasePermissions:
    FILES = ("index.html", "index_en.html", "console_data.json")

    @staticmethod
    def _mode(path) -> int:
        return stat.S_IMODE(os.stat(path).st_mode)

    def _assert_public_modes(self, output_dir: str, result: dict) -> None:
        release = Path(result["release_dir"])
        assert self._mode(output_dir) == 0o755
        assert self._mode(Path(output_dir, "releases")) == 0o755
        assert self._mode(release) == 0o755
        for name in self.FILES:
            assert self._mode(release / name) == 0o644
            assert self._mode(Path(output_dir, "current", name)) == 0o644

    def test_default_public_modes_and_current_target(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd, tempfile.TemporaryDirectory() as od:
            original_owner = (os.stat(od).st_uid, os.stat(od).st_gid)
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            result = generate_console(rd, od)
            assert result["success"] is True
            self._assert_public_modes(od, result)
            assert (os.stat(od).st_uid, os.stat(od).st_gid) == original_owner
            assert os.readlink(Path(od, "current")) == result["current_target"]

    def test_restrictive_umask_does_not_change_public_modes(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd, tempfile.TemporaryDirectory() as od:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            previous_umask = os.umask(0o077)
            try:
                result = generate_console(rd, od)
            finally:
                os.umask(previous_umask)
            assert result["success"] is True
            self._assert_public_modes(od, result)

    def test_file_mode_failure_preserves_last_good(self, monkeypatch):
        import scripts.generate_static_console as generator
        with tempfile.TemporaryDirectory() as rd, tempfile.TemporaryDirectory() as od:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            first = generator.generate_console(rd, od)
            assert first["success"] is True
            current = Path(od, "current")
            target = os.readlink(current)
            hashes = {name: (current / name).read_bytes() for name in self.FILES}
            modes = {name: self._mode(current / name) for name in self.FILES}

            def fail_file_mode(fd, path, mode):
                raise PermissionError("injected file mode failure")

            monkeypatch.setattr(generator, "_set_exact_fd_mode", fail_file_mode)
            second = generator.generate_console(rd, od)
            assert second["success"] is False
            assert os.readlink(current) == target
            assert all((current / name).read_bytes() == hashes[name] for name in self.FILES)
            assert all(self._mode(current / name) == modes[name] for name in self.FILES)
            assert not Path(od, "current.next").exists()
            assert not any(path.name.endswith(".tmp") for path in Path(od, "releases").iterdir())

    def test_release_directory_mode_failure_preserves_current(self, monkeypatch):
        import scripts.generate_static_console as generator
        with tempfile.TemporaryDirectory() as rd, tempfile.TemporaryDirectory() as od:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            first = generator.generate_console(rd, od)
            current = Path(od, "current")
            target = os.readlink(current)
            original = generator._set_exact_mode

            def fail_new_release(path, mode):
                if str(path).endswith(".tmp"):
                    raise PermissionError("injected release directory mode failure")
                original(path, mode)

            monkeypatch.setattr(generator, "_set_exact_mode", fail_new_release)
            second = generator.generate_console(rd, od)
            assert second["success"] is False
            assert os.readlink(current) == target
            assert Path(od, first["current_target"]).is_dir()
            assert not any(path.name.endswith(".tmp") for path in Path(od, "releases").iterdir())

    def test_historical_release_mode_is_not_changed(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd, tempfile.TemporaryDirectory() as od:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            first = generate_console(rd, od)
            historical = Path(first["release_dir"])
            os.chmod(historical, 0o711)
            second = generate_console(rd, od)
            assert second["success"] is True
            assert historical.is_dir()
            assert self._mode(historical) == 0o711
            self._assert_public_modes(od, second)

    def test_preserves_last_good_on_failure(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd:
            with tempfile.TemporaryDirectory() as od:
                _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
                r1 = generate_console(rd, od)
                assert r1["success"] is True
                v1 = r1["version_id"]
                current = os.path.join(od, "current")
                # Break lifecycle
                lc_path = os.path.join(rd, f"{_DATE}_shadow_lifecycle_result.json")
                with open(lc_path, "w") as f:
                    json.dump(_make_lifecycle(status="FAIL"), f)
                r2 = generate_console(rd, od)
                assert r2["success"] is False
                assert os.readlink(current) == f"releases/{v1}"


# ===========================================================================
# 17. Missing/corrupt input
# ===========================================================================

class TestInputValidation:
    def test_empty_dir_fails(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd:
            with tempfile.TemporaryDirectory() as od:
                result = generate_console(rd, od)
                assert result["success"] is False

    def test_missing_registry_fails(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd:
            with tempfile.TemporaryDirectory() as od:
                _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
                os.remove(os.path.join(rd, f"{_DATE}_shadow_run_registry.jsonl"))
                result = generate_console(rd, od)
                assert result["success"] is False
                assert any("registry" in e.lower() for e in result["errors"])


# ===========================================================================
# 18. Formal constructor chain
# ===========================================================================

class TestFormalConstructorChain:
    """Prove that the generator works with output from formal production constructors."""

    def test_full_chain_with_formal_constructors(self):
        """Ledger → compute_performance → build_run_record → ShadowSampleGateResult → generate."""
        from scripts.generate_static_console import generate_console

        with tempfile.TemporaryDirectory() as rd:
            with tempfile.TemporaryDirectory() as od:
                # 1. Write ledger
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                ledger_path = os.path.join(rd, f"{_DATE}_paper_position_ledger.jsonl")
                _write(ledger_path, [pos])

                # 2. Write lifecycle result BEFORE loading positions (needed for source verification)
                midpoint = _STARTED + _dt.timedelta(minutes=10)
                lc_result = _make_lifecycle(steps=_make_steps(
                    started=_STARTED_AT,
                    finished=midpoint.isoformat(timespec="seconds"),
                ))
                lc_result["finished_at"] = midpoint.isoformat(timespec="seconds")
                lc_path = os.path.join(rd, f"{_DATE}_shadow_lifecycle_result.json")
                with open(lc_path, "w") as f:
                    json.dump(lc_result, f)

                # 3. Compute scorecard via formal constructor
                eligible, all_canonical, diag = load_canonical_closed_clean_positions(rd)

                assert diag["accounting_status"] == "OK"
                scorecard = compute_performance(eligible, _DATE)
                sc_dict = scorecard.to_dict()
                sc_dict["cumulative_closed_clean"] = len(eligible)

                sc_path = os.path.join(rd, f"{_DATE}_paper_performance_scorecard.json")
                with open(sc_path, "w") as f:
                    json.dump(sc_dict, f)

                # 4. Build update result
                update_started = midpoint + _dt.timedelta(seconds=1)
                update_result = _make_update(steps=_make_steps(
                    started=update_started.isoformat(timespec="seconds"),
                    finished=_FINISHED_AT,
                ))
                update_result["started_at"] = update_started.isoformat(timespec="seconds")
                up_path = os.path.join(rd, f"{_DATE}_shadow_position_update_result.json")
                with open(up_path, "w") as f:
                    json.dump(update_result, f)

                # 5. Write the remaining formal runner outputs, then let the
                # production finalizer create the one authoritative record.
                with open(os.path.join(rd, f"{_DATE}_strategy_run_summary.json"), "w") as f:
                    json.dump({"candidate_count": 1}, f)
                with open(os.path.join(rd, f"{_DATE}_trade_intents.json"), "w") as f:
                    json.dump({"intent_count": 1, "status_counts": {"SHADOW_READY": 1}}, f)
                with open(os.path.join(rd, f"{_DATE}_paper_position_summary.json"), "w") as f:
                    json.dump({"status_counts": {"TAKE_PROFIT_HIT": 1},
                               "lifecycle_stats": {"new_positions_count": 0,
                                                   "existing_positions_count": 1,
                                                   "positions_updated_count": 1}}, f)
                with open(os.path.join(rd, f"{_DATE}_paper_positions_quarantine.json"), "w") as f:
                    json.dump({"quarantined_count": 0, "clean_count": 1}, f)

                from scripts.run_shadow_trading_lifecycle import finalize_batch_registry
                from core.paper_trading.shadow_run_registry import compute_sample_gate, read_registry
                finalize_batch_registry(_DATE, rd, _RUN_ID, _STARTED_AT)
                registry = read_registry(rd)
                assert len([r for r in registry if r["run_id"] == _RUN_ID]) == 1
                reg_dict = registry[0]

                # 6. Gate reads that final record through its formal constructor.
                gate = compute_sample_gate(rd)
                assert gate.latest_run_id == _RUN_ID
                gate_path = os.path.join(rd, f"{_DATE}_shadow_sample_gate.json")
                with open(gate_path, "w") as f:
                    json.dump(gate.to_dict(), f)

                # 7. Generate console
                result = generate_console(rd, od)
                assert result["success"] is True
                assert math.isinf(sc_dict["strategy_scorecards"][0]["profit_factor"])
                current = os.path.join(od, "current")
                with open(os.path.join(current, "console_data.json")) as f:
                    public = json.load(f)
                strategy = public["strategies"]["test_strat"]
                assert strategy["profit_factor"] is None
                assert strategy["profit_factor_status"] == "INFINITE"
                with open(os.path.join(current, "index.html")) as f:
                    assert "∞" in f.read()

                # 8. Verify six-way count
                from scripts.generate_static_console import validate_inputs
                bundle, errors = validate_inputs(rd)
                assert errors == []
                c = bundle["counts"]
                expected = len(eligible)
                assert c["canonical"] == expected
                assert c["scorecard_global"] == expected
                assert c["scorecard_strategy_sum"] == expected
                assert c["scorecard_cumulative"] == expected
                assert c["gate_cumulative"] == expected
                assert c["registry_cumulative"] == expected


class TestStrictTimeAndDateContract:
    @pytest.mark.parametrize("value", [
        "garbage", "2026-07-13", "2026-07-13T22:30:00", None,
    ])
    def test_timezone_aware_datetime_required(self, value):
        from scripts.generate_static_console import _parse_aware_iso_datetime
        assert _parse_aware_iso_datetime(value) is None

    @pytest.mark.parametrize("value", [
        "2026-7-3", "13/07/2026", "abc", "2026-02-30", "2026-13-01", None,
    ])
    def test_strict_calendar_date_required(self, value):
        from scripts.generate_static_console import _parse_iso_date
        assert _parse_iso_date(value) is None

    @pytest.mark.parametrize("field", ["started_at", "finished_at"])
    def test_invalid_step_time_blocks_generation(self, field):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as rd:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            path = os.path.join(rd, f"{_DATE}_shadow_lifecycle_result.json")
            data = json.load(open(path))
            data["steps"][0][field] = "garbage"
            with open(path, "w") as f:
                json.dump(data, f)
            _, errors = validate_inputs(rd)
            assert any(field in error for error in errors)


class TestLatestStepCompletionTimeline:
    @staticmethod
    def _set_steps(report_dir, suffix, finished_minutes):
        path = next(Path(report_dir).glob(f"*{suffix}"))
        data = json.load(open(path))
        now = _dt.datetime.now(_dt.timezone.utc)
        steps = []
        for index, minutes in enumerate(finished_minutes):
            finished = now - _dt.timedelta(minutes=minutes)
            started = finished - _dt.timedelta(minutes=1)
            steps.append({
                "step_name": f"step-{index}",
                "status": "PASS",
                "exit_code": 0,
                "started_at": started.isoformat(),
                "finished_at": finished.isoformat(),
            })
        data["steps"] = steps
        with open(path, "w") as f:
            json.dump(data, f)

    @staticmethod
    def _set_registry_finished(report_dir, minutes):
        path = next(Path(report_dir).glob("*_shadow_run_registry.jsonl"))
        record = json.loads(path.read_text().strip())
        finished = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(minutes=minutes)
        record["finished_at"] = finished.isoformat()
        record["started_at"] = (finished - _dt.timedelta(minutes=30)).isoformat()
        path.write_text(json.dumps(record) + "\n")

    @pytest.mark.parametrize("suffix,label", [
        ("_shadow_lifecycle_result.json", "Lifecycle"),
        ("_shadow_position_update_result.json", "Update"),
    ])
    def test_shuffled_latest_step_blocks_early_registry(self, suffix, label):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd, tempfile.TemporaryDirectory() as od:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            self._set_steps(rd, suffix, [1, 7])
            self._set_registry_finished(rd, 5)
            result = generate_console(rd, od)
            assert result["success"] is False
            assert any(f"{label} latest step" in error for error in result["errors"])

    def test_shuffled_steps_succeed_when_registry_is_latest(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd, tempfile.TemporaryDirectory() as od:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            self._set_steps(rd, "_shadow_lifecycle_result.json", [3, 10, 6])
            self._set_steps(rd, "_shadow_position_update_result.json", [3, 10, 6])
            self._set_registry_finished(rd, 1)
            assert generate_console(rd, od)["success"] is True

    def test_shuffled_failure_preserves_last_good(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as rd, tempfile.TemporaryDirectory() as od:
            _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
            first = generate_console(rd, od)
            assert first["success"] is True
            current = Path(od, "current")
            target = os.readlink(current)
            contents = {name: (current / name).read_bytes() for name in (
                "index.html", "index_en.html", "console_data.json",
            )}
            self._set_steps(rd, "_shadow_lifecycle_result.json", [1, 7])
            self._set_registry_finished(rd, 5)
            assert generate_console(rd, od)["success"] is False
            assert os.readlink(current) == target
            assert all((current / name).read_bytes() == data for name, data in contents.items())


def test_production_registry_filename_is_accepted():
    from scripts.generate_static_console import validate_inputs
    with tempfile.TemporaryDirectory() as rd:
        _write_full_report(rd, _pos("PP_001", "TAKE_PROFIT_HIT"))
        dated = next(Path(rd).glob("*_shadow_run_registry.jsonl"))
        dated.rename(Path(rd, "shadow_run_registry.jsonl"))
        _, errors = validate_inputs(rd)
        assert errors == []
