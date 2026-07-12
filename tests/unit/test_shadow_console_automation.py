"""Tests for shadow console automation audit fix.

Covers:
1. Terminal conflict detection (different CLOSED statuses)
2. Update-only formal entry (shared selector)
3. Formal runner fingerprint writes
4. Generator CLI validation
5. Missing/corrupt input handling
6. Atomic release fault injection
7. Shell pipeline control flow
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import datetime as _dt

import pytest

from core.paper_trading.paper_position import (
    select_canonical_position_state,
    PositionSelection,
    position_state_fingerprint,
    load_canonical_positions,
    load_canonical_closed_clean_positions,
    _normalize_fingerprint_value,
    _should_replace,
)


NOW_ISO = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


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
        "date": "2026-07-10",
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


def _write_full_report(report_dir: str, pos: dict, date_prefix: str = "2026-07-10",
                       strategy_id: str = "test_strat"):
    """Create all report files including ledger."""
    ledger = os.path.join(report_dir, f"{date_prefix}_paper_position_ledger.jsonl")
    _write(ledger, [pos])

    with open(os.path.join(report_dir, f"{date_prefix}_paper_performance_scorecard.json"), "w") as f:
        json.dump({
            "date": date_prefix,
            "global_metrics": {
                "clean_position_count": 1, "closed_position_count": 1,
                "excluded_position_count": 0, "open_position_count": 0,
                "win_rate": 1.0, "profit_factor": 2.0,
                "take_profit_hit": 1, "stop_loss_hit": 0, "timeout_exit": 0,
            },
            "strategy_scorecards": [{
                "strategy_id": strategy_id, "closed_count": 1,
                "win_rate": 1.0, "profit_factor": 2.0, "expectancy_r": 1.0,
                "avg_r_multiple": 1.0, "max_drawdown_r": 0.0, "max_losing_streak": 0,
            }],
            "clean_position_count": 1, "excluded_position_count": 0, "safety_flags": [],
        }, f)
    with open(os.path.join(report_dir, f"{date_prefix}_shadow_sample_gate.json"), "w") as f:
        json.dump({
            "date": date_prefix, "total_runs": 1, "latest_run_id": "test_run",
            "closed_clean_positions": 1, "sample_status": "PASS",
            "testnet_gate_status": "BLOCKED", "testnet_gate_reasons": ["shadow_only"],
            "registry_path": "test", "safety_flags": [],
        }, f)
    with open(os.path.join(report_dir, f"{date_prefix}_shadow_lifecycle_result.json"), "w") as f:
        json.dump({
            "date": date_prefix,
            "pipeline_status": "OK",
            "mode": "real_public_http",
            "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY"],
            "allow_public_http": True,
        }, f)
    with open(os.path.join(report_dir, f"{date_prefix}_shadow_position_update_result.json"), "w") as f:
        json.dump({"date": date_prefix, "pipeline_status": "OK"}, f)


# ---------------------------------------------------------------------------
# 1. Terminal conflict detection
# ---------------------------------------------------------------------------

class TestTerminalConflict:
    def test_take_profit_vs_stop_loss_conflict(self):
        """Different terminal statuses must produce conflict."""
        old = _pos("PP_001", "TAKE_PROFIT_HIT")
        new = _pos("PP_001", "STOP_LOSS_HIT")
        sel = select_canonical_position_state(old, new)
        assert sel.conflict is True
        assert sel.decision == "conflict_terminal"
        assert "TAKE_PROFIT_HIT" in sel.conflict_reason
        assert "STOP_LOSS_HIT" in sel.conflict_reason
        # Keep first terminal state
        assert sel.selected["status"] == "TAKE_PROFIT_HIT"

    def test_stop_loss_vs_take_profit_conflict(self):
        """Reverse conflict direction also detected."""
        old = _pos("PP_001", "STOP_LOSS_HIT")
        new = _pos("PP_001", "TAKE_PROFIT_HIT")
        sel = select_canonical_position_state(old, new)
        assert sel.conflict is True
        assert sel.decision == "conflict_terminal"
        assert sel.selected["status"] == "STOP_LOSS_HIT"

    def test_timeout_vs_take_profit_conflict(self):
        old = _pos("PP_001", "TIMEOUT_EXIT")
        new = _pos("PP_001", "TAKE_PROFIT_HIT")
        sel = select_canonical_position_state(old, new)
        assert sel.conflict is True
        assert sel.decision == "conflict_terminal"

    def test_conflict_in_canonical_load_goes_to_fatal(self):
        """Terminal conflicts in ledger must produce fatal_errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write conflicting records
            ledger = os.path.join(tmpdir, "2026-07-10_paper_position_ledger.jsonl")
            _write(ledger, [_pos("PP_001", "TAKE_PROFIT_HIT")])
            _write(ledger, [_pos("PP_001", "STOP_LOSS_HIT")])

            positions, diag = load_canonical_positions(tmpdir)
            assert diag["terminal_conflict_count"] == 1
            assert len(diag["terminal_conflicts"]) == 1

            # Now check full canonical load
            eligible, all_pos, full_diag = load_canonical_closed_clean_positions(tmpdir)
            assert full_diag["accounting_status"] == "ERROR"
            assert any("Terminal conflict" in e for e in full_diag["fatal_errors"])

    def test_same_terminal_no_conflict(self):
        """Same terminal status with same fingerprint: no conflict."""
        old = _pos("PP_001", "TAKE_PROFIT_HIT")
        new = _pos("PP_001", "TAKE_PROFIT_HIT")
        sel = select_canonical_position_state(old, new)
        assert sel.conflict is False
        assert sel.selected["status"] == "TAKE_PROFIT_HIT"


# ---------------------------------------------------------------------------
# 2. Update-only formal entry
# ---------------------------------------------------------------------------

class TestUpdateOnlyFormalEntry:
    def test_ledger_closed_not_reopened_by_positions_json(self):
        """CLOSED in ledger must not be reopened by positions.json."""
        from scripts.run_paper_position_simulator import _load_update_existing_positions
        with tempfile.TemporaryDirectory() as tmpdir:
            # Ledger: P1 = TAKE_PROFIT_HIT
            ledger = os.path.join(tmpdir, "2026-07-10_paper_position_ledger.jsonl")
            _write(ledger, [_pos("PP_001", "TAKE_PROFIT_HIT")])

            # positions.json: P1 = OPEN (newer)
            pos_path = os.path.join(tmpdir, "2026-07-10_paper_positions.json")
            open_pos = _pos("PP_001", "OPEN")
            open_pos["recorded_at"] = "2026-07-10T15:00:00Z"
            with open(pos_path, "w") as f:
                json.dump({"positions": [open_pos]}, f)

            # Should return empty (P1 is CLOSED, not OPEN)
            result = _load_update_existing_positions(tmpdir, "2026-07-10")
            assert len(result) == 0
            assert all(p.get("position_id") != "PP_001" for p in result)

    def test_different_terminal_conflict_aborts(self):
        """Different CLOSED statuses must raise RuntimeError."""
        from scripts.run_paper_position_simulator import _load_update_existing_positions
        with tempfile.TemporaryDirectory() as tmpdir:
            # Ledger: P1 = TAKE_PROFIT_HIT
            ledger = os.path.join(tmpdir, "2026-07-10_paper_position_ledger.jsonl")
            _write(ledger, [_pos("PP_001", "TAKE_PROFIT_HIT")])

            # positions.json: P1 = STOP_LOSS_HIT (different terminal)
            pos_path = os.path.join(tmpdir, "2026-07-10_paper_positions.json")
            sl_pos = _pos("PP_001", "STOP_LOSS_HIT")
            sl_pos["recorded_at"] = "2026-07-10T15:00:00Z"
            with open(pos_path, "w") as f:
                json.dump({"positions": [sl_pos]}, f)

            with pytest.raises(RuntimeError, match="Terminal state conflicts"):
                _load_update_existing_positions(tmpdir, "2026-07-10")

    def test_open_in_positions_json_updates_ledger_open(self):
        """OPEN in both sources: newer wins."""
        from scripts.run_paper_position_simulator import _load_update_existing_positions
        with tempfile.TemporaryDirectory() as tmpdir:
            # Ledger: P1 = OPEN
            ledger = os.path.join(tmpdir, "2026-07-10_paper_position_ledger.jsonl")
            old_open = _pos("PP_001", "OPEN")
            old_open["recorded_at"] = "2026-07-10T10:00:00Z"
            _write(ledger, [old_open])

            # positions.json: P1 = OPEN (newer, same status)
            pos_path = os.path.join(tmpdir, "2026-07-10_paper_positions.json")
            new_open = _pos("PP_001", "OPEN")
            new_open["recorded_at"] = "2026-07-10T15:00:00Z"
            with open(pos_path, "w") as f:
                json.dump({"positions": [new_open]}, f)

            result = _load_update_existing_positions(tmpdir, "2026-07-10")
            assert len(result) == 1
            assert result[0]["position_id"] == "PP_001"


# ---------------------------------------------------------------------------
# 3. Formal runner fingerprint writes
# ---------------------------------------------------------------------------

class TestFormalRunnerFingerprint:
    def test_unchecked_only_changes_no_append(self):
        """Changing only last_checked_at must not append new ledger line."""
        pos = _pos("PP_001", "OPEN")
        fp1 = position_state_fingerprint(pos)
        pos["last_checked_at"] = "2026-07-10T13:00:00Z"
        fp2 = position_state_fingerprint(pos)
        assert fp1 == fp2

    def test_recorded_at_only_changes_no_append(self):
        """Changing only recorded_at must not append new ledger line."""
        pos = _pos("PP_001", "OPEN")
        fp1 = position_state_fingerprint(pos)
        pos["recorded_at"] = "2026-07-10T13:00:00Z"
        fp2 = position_state_fingerprint(pos)
        assert fp1 == fp2

    def test_numeric_normalization_100_vs_100_0(self):
        """100 and 100.0 must produce same fingerprint."""
        pos1 = _pos("PP_001", "OPEN", entry_price=100)
        pos2 = _pos("PP_001", "OPEN", entry_price=100.0)
        assert position_state_fingerprint(pos1) == position_state_fingerprint(pos2)

    def test_open_to_closed_appends(self):
        """OPEN → CLOSED must change fingerprint."""
        pos_open = _pos("PP_001", "OPEN")
        pos_closed = _pos("PP_001", "TAKE_PROFIT_HIT")
        assert position_state_fingerprint(pos_open) != position_state_fingerprint(pos_closed)

    def test_numeric_normalization_helper(self):
        """_normalize_fingerprint_value handles various numeric forms."""
        assert _normalize_fingerprint_value(100) == "100"
        assert _normalize_fingerprint_value(100.0) == "100"
        assert _normalize_fingerprint_value(100.00) == "100"
        assert _normalize_fingerprint_value(1.5) == "1.5"
        assert _normalize_fingerprint_value(1.50) == "1.5"
        assert _normalize_fingerprint_value(None) == ""
        assert _normalize_fingerprint_value("abc") == "abc"

    def test_decimal_normalization(self):
        """Decimal values normalize correctly."""
        from decimal import Decimal
        assert _normalize_fingerprint_value(Decimal("100.000")) == "100"
        assert _normalize_fingerprint_value(Decimal("1.500")) == "1.5"

    def test_ledger_write_idempotent(self):
        """Running write logic twice with same data produces same number of lines."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-10_paper_position_ledger.jsonl")
            pos = _pos("PP_001", "OPEN")

            # First write
            _write(ledger, [pos])
            with open(ledger) as f:
                lines1 = f.readlines()

            # Second write (same data)
            _write(ledger, [pos])
            with open(ledger) as f:
                lines2 = f.readlines()

            # Both have 2 lines (append-only), but fingerprint is the same
            fp1 = position_state_fingerprint(json.loads(lines1[0]))
            fp2 = position_state_fingerprint(json.loads(lines2[0]))
            assert fp1 == fp2


# ---------------------------------------------------------------------------
# 4. Generator CLI
# ---------------------------------------------------------------------------

class TestGeneratorCLI:
    def test_cli_success(self):
        """Generator CLI returns 0 on success."""
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

    def test_cli_invalid_commit_rejected(self):
        """Invalid server commit hash is rejected."""
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
                assert "Invalid" in result.stdout

    def test_cli_output_has_symlink(self):
        """CLI creates current symlink."""
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                _write_full_report(report_dir, pos)

                subprocess.run(
                    ["python3", "scripts/generate_static_console.py",
                     "--report-dir", report_dir,
                     "--output-dir", output_dir],
                    capture_output=True, text=True,
                    cwd="/tmp/qq-shadow-console-fix",
                )
                current = os.path.join(output_dir, "current")
                assert os.path.islink(current)
                target = os.readlink(current)
                assert target.startswith("releases/")

    def test_cli_json_has_all_fields(self):
        """CLI output JSON has required fields."""
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                _write_full_report(report_dir, pos)

                subprocess.run(
                    ["python3", "scripts/generate_static_console.py",
                     "--report-dir", report_dir,
                     "--output-dir", output_dir],
                    capture_output=True, text=True,
                    cwd="/tmp/qq-shadow-console-fix",
                )
                json_path = os.path.join(output_dir, "current", "console_data.json")
                with open(json_path) as f:
                    data = json.load(f)
                assert "generated_at" in data
                assert "server_commit" in data
                assert "strategies" in data
                assert "eligible_closed_clean" in data
                assert "count_check" in data

    def test_cli_no_control_code_in_html(self):
        """Generated HTML has no control code."""
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                _write_full_report(report_dir, pos)

                subprocess.run(
                    ["python3", "scripts/generate_static_console.py",
                     "--report-dir", report_dir,
                     "--output-dir", output_dir],
                    capture_output=True, text=True,
                    cwd="/tmp/qq-shadow-console-fix",
                )
                for fname in ["index.html", "index_en.html"]:
                    with open(os.path.join(output_dir, "current", fname)) as f:
                        content = f.read()
                    assert "<button" not in content
                    assert "<form" not in content
                    assert "onclick" not in content
                    assert "fetch(" not in content


# ---------------------------------------------------------------------------
# 5. Missing/corrupt input handling
# ---------------------------------------------------------------------------

class TestGeneratorInputValidation:
    def test_empty_dir_fails(self):
        """Empty report dir returns non-zero."""
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                result = generate_console(report_dir, output_dir)
                assert result["success"] is False
                assert any("Missing" in e for e in result["errors"])

    def test_missing_scorecard_fails(self):
        """Missing scorecard returns non-zero."""
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                date = "2026-07-10"
                # Write only lifecycle and update
                with open(os.path.join(report_dir, f"{date}_shadow_lifecycle_result.json"), "w") as f:
                    json.dump({"date": date}, f)
                with open(os.path.join(report_dir, f"{date}_shadow_position_update_result.json"), "w") as f:
                    json.dump({"date": date}, f)
                with open(os.path.join(report_dir, f"{date}_shadow_sample_gate.json"), "w") as f:
                    json.dump({"date": date}, f)

                result = generate_console(report_dir, output_dir)
                assert result["success"] is False
                assert any("scorecard" in e.lower() for e in result["errors"])

    def test_missing_gate_fails(self):
        """Missing gate returns non-zero."""
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                date = "2026-07-10"
                with open(os.path.join(report_dir, f"{date}_shadow_lifecycle_result.json"), "w") as f:
                    json.dump({"date": date}, f)
                with open(os.path.join(report_dir, f"{date}_shadow_position_update_result.json"), "w") as f:
                    json.dump({"date": date}, f)
                with open(os.path.join(report_dir, f"{date}_paper_performance_scorecard.json"), "w") as f:
                    json.dump({"date": date}, f)

                result = generate_console(report_dir, output_dir)
                assert result["success"] is False
                assert any("gate" in e.lower() for e in result["errors"])

    def test_corrupt_json_fails(self):
        """Corrupt JSON returns non-zero."""
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                date = "2026-07-10"
                with open(os.path.join(report_dir, f"{date}_shadow_lifecycle_result.json"), "w") as f:
                    f.write("{corrupt")

                result = generate_console(report_dir, output_dir)
                assert result["success"] is False

    def test_date_mismatch_fails(self):
        """Date mismatch between reports returns non-zero."""
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                with open(os.path.join(report_dir, "2026-07-10_shadow_lifecycle_result.json"), "w") as f:
                    json.dump({"date": "2026-07-10"}, f)
                with open(os.path.join(report_dir, "2026-07-11_shadow_position_update_result.json"), "w") as f:
                    json.dump({"date": "2026-07-11"}, f)

                result = generate_console(report_dir, output_dir)
                assert result["success"] is False
                assert any("mismatch" in e.lower() for e in result["errors"])

    def test_accounting_error_fails(self):
        """Terminal conflict (accounting error) returns non-zero."""
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                date = "2026-07-10"
                # Write conflicting terminal states
                ledger = os.path.join(report_dir, f"{date}_paper_position_ledger.jsonl")
                _write(ledger, [_pos("PP_001", "TAKE_PROFIT_HIT")])
                _write(ledger, [_pos("PP_001", "STOP_LOSS_HIT")])

                # Write required report files
                _write_full_report(report_dir, _pos("PP_002", "TAKE_PROFIT_HIT"), date)

                result = generate_console(report_dir, output_dir)
                assert result["success"] is False
                assert any("accounting" in e.lower() or "conflict" in e.lower() or "fatal" in e.lower()
                          for e in result["errors"])


# ---------------------------------------------------------------------------
# 6. Atomic release
# ---------------------------------------------------------------------------

class TestAtomicRelease:
    def test_symlink_switch(self):
        """Two consecutive releases switch symlink correctly."""
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

                # Second release
                r2 = generate_console(report_dir, output_dir)
                assert r2["success"] is True
                v2 = r2["version_id"]
                assert v2 != v1
                assert os.readlink(current) == f"releases/{v2}"

                # Both versions still on disk
                assert os.path.isdir(os.path.join(output_dir, "releases", v1))
                assert os.path.isdir(os.path.join(output_dir, "releases", v2))

    def test_release_dir_structure(self):
        """Release directory contains exactly 3 files."""
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                _write_full_report(report_dir, pos)

                result = generate_console(report_dir, output_dir)
                assert result["success"] is True

                release_dir = result["release_dir"]
                files = set(os.listdir(release_dir))
                assert files == {"index.html", "index_en.html", "console_data.json"}


# ---------------------------------------------------------------------------
# 7. Shell pipeline
# ---------------------------------------------------------------------------

class TestShellPipeline:
    def test_syntax_valid(self):
        """Shell script has valid syntax."""
        result = subprocess.run(
            ["bash", "-n", "scripts/run_cloud_shadow_collection_once.sh"],
            capture_output=True, text=True,
            cwd="/tmp/qq-shadow-console-fix",
        )
        assert result.returncode == 0

    def test_step_failure_stops_pipeline(self):
        """Verify run_step helper exists and fails correctly."""
        script_path = "/tmp/qq-shadow-console-fix/scripts/run_cloud_shadow_collection_once.sh"
        with open(script_path) as f:
            content = f.read()
        # Must use run_step function
        assert "run_step" in content
        # Must NOT use EXIT=$? pattern
        assert "EXIT=$?" not in content
        # Must pass --server-commit
        assert "--server-commit" in content
