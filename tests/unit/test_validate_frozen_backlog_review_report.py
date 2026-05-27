"""T1622 - Tests for validate_frozen_backlog_review_report.py CLI.

Runs the CLI via subprocess. Validates exit codes and output.
No network. No live. No submit.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = str(
    Path(__file__).resolve().parent.parent.parent
    / "scripts"
    / "validate_frozen_backlog_review_report.py"
)

_GENERATE_SCRIPT = str(
    Path(__file__).resolve().parent.parent.parent
    / "scripts"
    / "generate_frozen_backlog_review_report.py"
)

# Canonical correct report for testing
_CORRECT_SUMMARY = {
    "summary_id": "summary-frozen-backlog-batch1",
    "total_files": 22,
    "high_risk_count": 9,
    "medium_risk_count": 13,
    "release_hold": "HOLD",
    "no_live": True,
    "no_submit": True,
    "no_exchange": True,
    "no_runtime_integration": True,
    "no_planner_integration": True,
}

_CORRECT_RECORD_TEMPLATE = {
    "record_id": "report-0000",
    "file_path": "core/live_runner.py",
    "risk_class": "HIGH",
    "category": "LIVE_RUNNER",
    "allowed_actions": ["review", "read", "lint", "typecheck"],
    "forbidden_actions": ["execute", "import_runtime", "submit", "modify"],
    "required_evidence": ["dry_run_log", "risk_review", "human_approval"],
    "readiness_score": 0.0,
    "unlock_recommendation": "HOLD",
    "release_hold": "HOLD",
}


def _make_correct_report() -> dict:
    records = []
    for i in range(22):
        rec = copy.deepcopy(_CORRECT_RECORD_TEMPLATE)
        rec["record_id"] = f"report-{i:04d}"
        rec["file_path"] = f"frozen/file_{i:02d}.py"
        records.append(rec)
    return {
        "summary": copy.deepcopy(_CORRECT_SUMMARY),
        "records": records,
    }


def _write_report(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")
    return str(path)


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, _SCRIPT, *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestValidateCLI:
    """Tests for the validate CLI script."""

    def test_valid_report_exit_zero(self, tmp_path: Path) -> None:
        report_path = _write_report(tmp_path / "report.json", _make_correct_report())
        result = _run_cli("--input-json", report_path)
        assert result.returncode == 0, result.stdout

    def test_valid_report_stdout_contains_pass(self, tmp_path: Path) -> None:
        report_path = _write_report(tmp_path / "report.json", _make_correct_report())
        result = _run_cli("--input-json", report_path)
        assert "PASS" in result.stdout

    def test_wrong_total_files_exit_one(self, tmp_path: Path) -> None:
        data = _make_correct_report()
        data["summary"]["total_files"] = 10
        report_path = _write_report(tmp_path / "bad.json", data)
        result = _run_cli("--input-json", report_path)
        assert result.returncode == 1

    def test_wrong_total_files_stdout_contains_fail(self, tmp_path: Path) -> None:
        data = _make_correct_report()
        data["summary"]["total_files"] = 10
        report_path = _write_report(tmp_path / "bad.json", data)
        result = _run_cli("--input-json", report_path)
        assert "FAIL" in result.stdout

    def test_missing_file_exit_one(self, tmp_path: Path) -> None:
        result = _run_cli("--input-json", str(tmp_path / "nonexistent.json"))
        assert result.returncode == 1
        assert "FAIL" in result.stdout

    def test_custom_expected_total(self, tmp_path: Path) -> None:
        data = _make_correct_report()
        # Change total and record count to match custom expected
        data["summary"]["total_files"] = 5
        data["records"] = data["records"][:5]
        report_path = _write_report(tmp_path / "custom.json", data)
        # Core validator expects 22, so this will fail at core level
        # but the CLI --expected-total is used for extra check
        result = _run_cli(
            "--input-json", report_path,
            "--expected-total", "5",
            "--expected-high", "9",
            "--expected-medium", "13",
        )
        # Core validator enforces 22 records, so will fail on records_count_match
        assert result.returncode == 1

    def test_json_input_not_json_exit_one(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("not json", encoding="utf-8")
        result = _run_cli("--input-json", str(bad))
        assert result.returncode == 1
        assert "FAIL" in result.stdout

    def test_stdout_contains_check_counts(self, tmp_path: Path) -> None:
        report_path = _write_report(tmp_path / "report.json", _make_correct_report())
        result = _run_cli("--input-json", report_path)
        assert "Checks passed:" in result.stdout
        assert "Checks failed:" in result.stdout

    def test_wrong_release_hold_exit_one(self, tmp_path: Path) -> None:
        data = _make_correct_report()
        data["summary"]["release_hold"] = "RELEASED"
        report_path = _write_report(tmp_path / "bad.json", data)
        result = _run_cli("--input-json", report_path)
        assert result.returncode == 1
        assert "FAIL" in result.stdout

    def test_help_exits_zero(self) -> None:
        result = _run_cli("--help")
        assert result.returncode == 0
        assert "frozen backlog report" in result.stdout.lower()
