"""Tests for shadow console automation audit fix.

Covers:
1. Terminal conflict detection (different CLOSED statuses)
2. Update-only formal entry (shared selector)
3. Formal runner fingerprint writes
4. Generator CLI validation
5. Missing/corrupt input handling
6. Atomic release fault injection
7. Shell pipeline control flow
8. Production schema compatibility
9. Six-way accounting count
10. HTML injection safety
11. NaN/Infinity fail-closed
12. Run validation (lifecycle/update PASS/FAIL)
13. Release retention
14. Nginx path contract
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import tempfile
import datetime as _dt
from decimal import Decimal

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


NOW_ISO = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
_RUN_ID = "test_run_20260712_001"
_DATE = "2026-07-12"
_FINISHED_AT = "2026-07-12T22:30:00+08:00"


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


def _make_scorecard(date: str = _DATE, closed: int = 1, cumulative: int = 1) -> dict:
    """Production-schema Scorecard JSON."""
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
        "strategy_scorecards": [{
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
        }],
        "clean_position_count": closed,
        "excluded_position_count": 0,
        "cumulative_closed_clean": cumulative,
        "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY"],
    }


def _make_gate(date: str = _DATE, cumulative: int = 1) -> dict:
    """Production-schema Gate JSON."""
    return {
        "date": date,
        "total_runs": 1,
        "latest_run_id": _RUN_ID,
        "closed_clean_positions": cumulative,
        "cumulative_closed_clean": cumulative,
        "sample_status": "PASS",
        "testnet_gate_status": "BLOCKED",
        "testnet_gate_reasons": ["shadow_only"],
        "registry_path": "test",
        "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY"],
    }


def _make_lifecycle(date: str = _DATE, status: str = "PASS") -> dict:
    """Production-schema Lifecycle result."""
    return {
        "date": date,
        "mode": "real_public_http",
        "allow_public_http": True,
        "pipeline_status": status,
        "steps": [{
            "step_name": "lifecycle",
            "command": "test",
            "started_at": "2026-07-12T22:00:00+08:00",
            "finished_at": _FINISHED_AT,
            "duration_seconds": 30,
            "exit_code": 0,
            "status": status,
            "stdout_tail": "",
            "stderr_tail": "",
        }],
        "summary": {},
        "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY"],
        "run_id": _RUN_ID,
        "sample_gate_status": "BLOCKED",
        "sample_gate_reasons": ["shadow_only"],
        "registry_written": True,
        "registry_path": "test",
    }


def _make_update(date: str = _DATE, status: str = "PASS") -> dict:
    """Production-schema Update result."""
    return {
        "date": date,
        "mode": "real_public_http",
        "pipeline_type": "update_only",
        "allow_public_http": True,
        "pipeline_status": status,
        "steps": [{
            "step_name": "update_only",
            "command": "test",
            "started_at": "2026-07-12T22:15:00+08:00",
            "finished_at": _FINISHED_AT,
            "duration_seconds": 10,
            "exit_code": 0,
            "status": status,
            "stdout_tail": "",
            "stderr_tail": "",
        }],
        "summary": {},
        "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY"],
        "run_id": _RUN_ID,
    }


def _make_registry(date: str = _DATE, cumulative: int = 1) -> dict:
    """Production-schema Registry record."""
    return {
        "run_id": _RUN_ID,
        "date": date,
        "started_at": "2026-07-12T22:00:00+08:00",
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
                       update_status: str = "PASS"):
    """Create all report files with production schemas."""
    # Ledger
    ledger = os.path.join(report_dir, f"{date}_paper_position_ledger.jsonl")
    _write(ledger, [pos])

    # Scorecard (production schema)
    with open(os.path.join(report_dir, f"{date}_paper_performance_scorecard.json"), "w") as f:
        json.dump(_make_scorecard(date, closed=1, cumulative=cumulative), f)

    # Gate (production schema)
    with open(os.path.join(report_dir, f"{date}_shadow_sample_gate.json"), "w") as f:
        json.dump(_make_gate(date, cumulative=cumulative), f)

    # Lifecycle (production schema)
    with open(os.path.join(report_dir, f"{date}_shadow_lifecycle_result.json"), "w") as f:
        json.dump(_make_lifecycle(date, lc_status), f)

    # Update (production schema)
    with open(os.path.join(report_dir, f"{date}_shadow_position_update_result.json"), "w") as f:
        json.dump(_make_update(date, update_status), f)

    # Registry (production schema)
    with open(os.path.join(report_dir, f"{date}_shadow_run_registry.jsonl"), "a") as f:
        f.write(json.dumps(_make_registry(date, cumulative)) + "\n")


# ---------------------------------------------------------------------------
# 1. Terminal conflict detection
# ---------------------------------------------------------------------------

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
        assert sel.selected["r_multiple"] == 1.0  # keep first

    def test_closed_to_open_regression(self):
        old = _pos("PP_001", "TAKE_PROFIT_HIT")
        new = _pos("PP_001", "OPEN")
        sel = select_canonical_position_state(old, new)
        assert sel.conflict is True
        assert sel.conflict_reason == "terminal_irreversible"
        assert sel.selected["status"] == "TAKE_PROFIT_HIT"

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
            assert any("Terminal conflict" in e for e in diag["fatal_errors"])

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


# ---------------------------------------------------------------------------
# 2. Update-only formal entry
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 3. Fingerprint
# ---------------------------------------------------------------------------

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
        assert isinstance(result, str)

    def test_positive_inf_fingerprint(self):
        result = _normalize_fingerprint_value(float("inf"))
        assert result == "NON_FINITE_POS_INF"

    def test_negative_inf_fingerprint(self):
        result = _normalize_fingerprint_value(float("-inf"))
        assert result == "NON_FINITE_NEG_INF"

    def test_decimal_nan(self):
        result = _normalize_fingerprint_value(Decimal("NaN"))
        assert result == "NON_FINITE_NAN"

    def test_decimal_inf(self):
        result = _normalize_fingerprint_value(Decimal("Infinity"))
        assert result == "NON_FINITE_POS_INF"

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
        """Non-finite values in accounting fields → fatal error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use exit_price=NaN (not entry_price, since NaN is falsy and
            # would be filtered by the entry_price truthiness check before
            # the non-finite check runs)
            pos = _pos("PP_001", "TAKE_PROFIT_HIT")
            pos["exit_price"] = float("nan")
            ledger = os.path.join(tmpdir, f"{_DATE}_paper_position_ledger.jsonl")
            _write(ledger, [pos])
            # Write lifecycle metadata so source check passes
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
            # Write lifecycle metadata so source check passes
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


# ---------------------------------------------------------------------------
# 4. Six-way accounting count
# ---------------------------------------------------------------------------

class TestSixWayCount:
    def test_all_six_match(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as report_dir:
            pos = _pos("PP_001", "TAKE_PROFIT_HIT")
            _write_full_report(report_dir, pos, cumulative=1)

            bundle, errors = validate_inputs(report_dir)
            assert errors == []
            counts = bundle["counts"]
            assert counts["canonical"] == 1
            assert counts["scorecard_global"] == 1
            assert counts["scorecard_strategy_sum"] == 1
            assert counts["scorecard_cumulative"] == 1
            assert counts["gate_cumulative"] == 1
            assert counts["registry_cumulative"] == 1

    def test_count_mismatch_fails(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as report_dir:
            pos = _pos("PP_001", "TAKE_PROFIT_HIT")
            _write_full_report(report_dir, pos, cumulative=1)
            # Corrupt scorecard to have wrong count
            sc_path = os.path.join(report_dir, f"{_DATE}_paper_performance_scorecard.json")
            sc = _make_scorecard(cumulative=99)
            with open(sc_path, "w") as f:
                json.dump(sc, f)

            bundle, errors = validate_inputs(report_dir)
            assert any("Count mismatch" in e for e in errors)


# ---------------------------------------------------------------------------
# 5. Run validation
# ---------------------------------------------------------------------------

class TestRunValidation:
    def test_lifecycle_fail_blocks(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                _write_full_report(report_dir, pos, lc_status="FAIL")
                result = generate_console(report_dir, output_dir)
                assert result["success"] is False
                assert any("Lifecycle" in e and "not PASS" in e for e in result["errors"])

    def test_update_fail_blocks(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                _write_full_report(report_dir, pos, update_status="FAIL")
                result = generate_console(report_dir, output_dir)
                assert result["success"] is False
                assert any("Update" in e and "not PASS" in e for e in result["errors"])

    def test_missing_completion_time_blocks(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as report_dir:
            pos = _pos("PP_001", "TAKE_PROFIT_HIT")
            _write_full_report(report_dir, pos)
            # Remove steps from lifecycle (no finished_at)
            lc_path = os.path.join(report_dir, f"{_DATE}_shadow_lifecycle_result.json")
            lc = _make_lifecycle()
            lc["steps"] = []
            with open(lc_path, "w") as f:
                json.dump(lc, f)
            # Also fix registry to not have finished_at
            reg_path = os.path.join(report_dir, f"{_DATE}_shadow_run_registry.jsonl")
            reg = _make_registry()
            reg["finished_at"] = ""
            with open(reg_path, "w") as f:
                f.write(json.dumps(reg) + "\n")

            bundle, errors = validate_inputs(report_dir)
            assert any("completion time" in e.lower() for e in errors)

    def test_date_only_rejected(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as report_dir:
            pos = _pos("PP_001", "TAKE_PROFIT_HIT")
            _write_full_report(report_dir, pos)
            # Set registry finished_at to date-only
            reg_path = os.path.join(report_dir, f"{_DATE}_shadow_run_registry.jsonl")
            reg = _make_registry()
            reg["finished_at"] = "2026-07-12"
            with open(reg_path, "w") as f:
                f.write(json.dumps(reg) + "\n")
            # Also clear lifecycle steps so it can't fall back to lifecycle time
            lc_path = os.path.join(report_dir, f"{_DATE}_shadow_lifecycle_result.json")
            lc = _make_lifecycle()
            lc["steps"] = []
            with open(lc_path, "w") as f:
                json.dump(lc, f)

            bundle, errors = validate_inputs(report_dir)
            assert any("completion time" in e.lower() for e in errors)

    def test_registry_accounting_error_blocks(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as report_dir:
            pos = _pos("PP_001", "TAKE_PROFIT_HIT")
            _write_full_report(report_dir, pos)
            reg_path = os.path.join(report_dir, f"{_DATE}_shadow_run_registry.jsonl")
            reg = _make_registry()
            reg["accounting_status"] = "ERROR"
            with open(reg_path, "w") as f:
                f.write(json.dumps(reg) + "\n")

            bundle, errors = validate_inputs(report_dir)
            assert any("accounting_status" in e for e in errors)


# ---------------------------------------------------------------------------
# 6. HTML injection safety
# ---------------------------------------------------------------------------

class TestHtmlSafety:
    def test_symbol_injection_escaped(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT",
                           symbol='<img src=x onerror=alert(1)>')
                _write_full_report(report_dir, pos)
                result = generate_console(report_dir, output_dir)
                assert result["success"] is True
                current = os.path.join(output_dir, "current")
                for fname in ["index.html", "index_en.html"]:
                    with open(os.path.join(current, fname)) as f:
                        content = f.read()
                    assert "<img" not in content
                    # onerror survives as escaped text (safe — not in a tag)
                    assert "&lt;img" in content

    def test_strategy_injection_escaped(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT",
                           strategy_id='<script>alert(1)</script>')
                _write_full_report(report_dir, pos)
                result = generate_console(report_dir, output_dir)
                assert result["success"] is True
                current = os.path.join(output_dir, "current")
                for fname in ["index.html", "index_en.html"]:
                    with open(os.path.join(current, fname)) as f:
                        content = f.read()
                    assert "<script>" not in content
                    assert "&lt;script&gt;" in content

    def test_exit_reason_injection_escaped(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT",
                           exit_reason='</td><script>alert(1)</script>')
                _write_full_report(report_dir, pos)
                result = generate_console(report_dir, output_dir)
                assert result["success"] is True
                current = os.path.join(output_dir, "current")
                for fname in ["index.html", "index_en.html"]:
                    with open(os.path.join(current, fname)) as f:
                        content = f.read()
                    assert "<script>" not in content
                    assert "javascript:" not in content

    def test_no_javascript_href(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                _write_full_report(report_dir, pos)
                result = generate_console(report_dir, output_dir)
                assert result["success"] is True
                current = os.path.join(output_dir, "current")
                for fname in ["index.html", "index_en.html"]:
                    with open(os.path.join(current, fname)) as f:
                        content = f.read()
                    assert "javascript:" not in content


# ---------------------------------------------------------------------------
# 7. Shell pipeline
# ---------------------------------------------------------------------------

class TestShellPipeline:
    def test_syntax_valid(self):
        result = subprocess.run(
            ["bash", "-n", "scripts/run_cloud_shadow_collection_once.sh"],
            capture_output=True, text=True,
            cwd="/tmp/qq-shadow-console-fix",
        )
        assert result.returncode == 0

    def test_run_step_exists(self):
        with open("/tmp/qq-shadow-console-fix/scripts/run_cloud_shadow_collection_once.sh") as f:
            content = f.read()
        assert "run_step" in content
        assert "EXIT=$?" not in content
        assert "--server-commit" in content
        assert "local rc=$?" in content

    def test_exit_code_captured(self):
        """Verify shell script captures real exit code, not 0."""
        with open("/tmp/qq-shadow-console-fix/scripts/run_cloud_shadow_collection_once.sh") as f:
            content = f.read()
        # The run_step function must capture rc before echoing
        assert 'local rc=$?' in content
        assert 'exit=${rc}' in content


# ---------------------------------------------------------------------------
# 8. Generator CLI
# ---------------------------------------------------------------------------

class TestGeneratorCLI:
    def test_cli_success(self):
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                _write_full_report(report_dir, pos)
                result = subprocess.run(
                    ["python3", "scripts/generate_static_console.py",
                     "--report-dir", report_dir,
                     "--output-dir", output_dir,
                     "--server-commit", "abc1234"],
                    capture_output=True, text=True,
                    cwd="/tmp/qq-shadow-console-fix",
                )
                assert result.returncode == 0
                assert "version=" in result.stdout
                assert "public_root:" in result.stdout
                assert "required_nginx_alias:" in result.stdout

    def test_cli_invalid_commit_rejected(self):
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                result = subprocess.run(
                    ["python3", "scripts/generate_static_console.py",
                     "--report-dir", report_dir,
                     "--output-dir", output_dir,
                     "--server-commit", "not-a-hash!"],
                    capture_output=True, text=True,
                    cwd="/tmp/qq-shadow-console-fix",
                )
                assert result.returncode == 1

    def test_cli_lifecycle_fail_blocks(self):
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                _write_full_report(report_dir, pos, lc_status="FAIL")
                result = subprocess.run(
                    ["python3", "scripts/generate_static_console.py",
                     "--report-dir", report_dir,
                     "--output-dir", output_dir],
                    capture_output=True, text=True,
                    cwd="/tmp/qq-shadow-console-fix",
                )
                assert result.returncode == 1
                assert "FAILED" in result.stdout


# ---------------------------------------------------------------------------
# 9. Nginx path contract
# ---------------------------------------------------------------------------

class TestNginxPathContract:
    def test_no_root_level_files(self):
        """Public files only in current/, not in root output dir."""
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                _write_full_report(report_dir, pos)
                result = generate_console(report_dir, output_dir)
                assert result["success"] is True
                # Root level should NOT have index.html
                assert not os.path.isfile(os.path.join(output_dir, "index.html"))
                assert not os.path.isfile(os.path.join(output_dir, "console_data.json"))
                # current/ should have them
                current = os.path.join(output_dir, "current")
                assert os.path.isfile(os.path.join(current, "index.html"))
                assert os.path.isfile(os.path.join(current, "console_data.json"))

    def test_current_is_symlink(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                _write_full_report(report_dir, pos)
                result = generate_console(report_dir, output_dir)
                assert result["success"] is True
                current = os.path.join(output_dir, "current")
                assert os.path.islink(current)
                assert result["public_root"].endswith("/current")
                assert result["required_nginx_alias"].endswith("/current/")


# ---------------------------------------------------------------------------
# 10. Release retention
# ---------------------------------------------------------------------------

class TestReleaseRetention:
    def test_max_releases_kept(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                _write_full_report(report_dir, pos)
                # Generate 8 releases
                for _ in range(8):
                    result = generate_console(report_dir, output_dir)
                    assert result["success"] is True

                releases_dir = os.path.join(output_dir, "releases")
                remaining = [
                    d for d in os.listdir(releases_dir)
                    if os.path.isdir(os.path.join(releases_dir, d))
                ]
                # Should keep at most 5
                assert len(remaining) <= 5

    def test_current_not_deleted(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                _write_full_report(report_dir, pos)
                for _ in range(8):
                    result = generate_console(report_dir, output_dir)

                current = os.path.join(output_dir, "current")
                assert os.path.islink(current)
                target = os.readlink(current)
                assert os.path.isdir(os.path.join(output_dir, target))


# ---------------------------------------------------------------------------
# 11. Atomic release
# ---------------------------------------------------------------------------

class TestAtomicRelease:
    def test_symlink_switch(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                _write_full_report(report_dir, pos)
                r1 = generate_console(report_dir, output_dir)
                assert r1["success"] is True
                v1 = r1["version_id"]
                current = os.path.join(output_dir, "current")
                assert os.readlink(current) == f"releases/{v1}"
                r2 = generate_console(report_dir, output_dir)
                assert r2["success"] is True
                v2 = r2["version_id"]
                assert v2 != v1
                assert os.readlink(current) == f"releases/{v2}"

    def test_preserves_last_good_on_failure(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                _write_full_report(report_dir, pos)
                r1 = generate_console(report_dir, output_dir)
                assert r1["success"] is True
                v1 = r1["version_id"]
                current = os.path.join(output_dir, "current")
                # Break lifecycle
                lc_path = os.path.join(report_dir, f"{_DATE}_shadow_lifecycle_result.json")
                with open(lc_path, "w") as f:
                    json.dump(_make_lifecycle(status="FAIL"), f)
                r2 = generate_console(report_dir, output_dir)
                assert r2["success"] is False
                assert os.readlink(current) == f"releases/{v1}"


# ---------------------------------------------------------------------------
# 12. Missing/corrupt input
# ---------------------------------------------------------------------------

class TestInputValidation:
    def test_empty_dir_fails(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                result = generate_console(report_dir, output_dir)
                assert result["success"] is False

    def test_missing_registry_fails(self):
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                _write_full_report(report_dir, pos)
                # Remove registry
                os.remove(os.path.join(report_dir, f"{_DATE}_shadow_run_registry.jsonl"))
                result = generate_console(report_dir, output_dir)
                assert result["success"] is False
                assert any("registry" in e.lower() for e in result["errors"])

    def test_registry_wrong_run_id_fails(self):
        from scripts.generate_static_console import validate_inputs
        with tempfile.TemporaryDirectory() as report_dir:
            pos = _pos("PP_001", "TAKE_PROFIT_HIT")
            _write_full_report(report_dir, pos)
            reg_path = os.path.join(report_dir, f"{_DATE}_shadow_run_registry.jsonl")
            reg = _make_registry()
            reg["run_id"] = "wrong_run_id"
            with open(reg_path, "w") as f:
                f.write(json.dumps(reg) + "\n")

            bundle, errors = validate_inputs(report_dir)
            assert any("Registry missing" in e for e in errors)
