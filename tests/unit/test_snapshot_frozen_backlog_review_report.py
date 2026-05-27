"""T1623 - Tests for snapshot_frozen_backlog_review_report.py CLI.

Runs the CLI via subprocess. Validates snapshot file creation.
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
    / "snapshot_frozen_backlog_review_report.py"
)

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


class TestSnapshotCLI:
    """Tests for the snapshot CLI script."""

    def test_snapshot_creates_file(self, tmp_path: Path) -> None:
        report_path = _write_report(tmp_path / "report.json", _make_correct_report())
        snap_path = str(tmp_path / "snap.json")
        result = _run_cli("--input-json", report_path, "--output-snapshot", snap_path)
        assert result.returncode == 0, result.stderr
        assert Path(snap_path).exists()

    def test_snapshot_valid_json(self, tmp_path: Path) -> None:
        report_path = _write_report(tmp_path / "report.json", _make_correct_report())
        snap_path = str(tmp_path / "snap.json")
        _run_cli("--input-json", report_path, "--output-snapshot", snap_path)
        data = json.loads(Path(snap_path).read_text(encoding="utf-8"))
        assert "snapshot_id" in data
        assert "report_data" in data
        assert "created_at_iso" in data
        assert "version" in data

    def test_snapshot_preserves_report_data(self, tmp_path: Path) -> None:
        report = _make_correct_report()
        report_path = _write_report(tmp_path / "report.json", report)
        snap_path = str(tmp_path / "snap.json")
        _run_cli("--input-json", report_path, "--output-snapshot", snap_path)
        data = json.loads(Path(snap_path).read_text(encoding="utf-8"))
        assert data["report_data"]["summary"]["total_files"] == 22
        assert len(data["report_data"]["records"]) == 22

    def test_stdout_contains_confirmation(self, tmp_path: Path) -> None:
        report_path = _write_report(tmp_path / "report.json", _make_correct_report())
        snap_path = str(tmp_path / "snap.json")
        result = _run_cli("--input-json", report_path, "--output-snapshot", snap_path)
        assert "Snapshot written to" in result.stdout
        assert "Snapshot ID:" in result.stdout

    def test_missing_input_exit_one(self, tmp_path: Path) -> None:
        snap_path = str(tmp_path / "snap.json")
        result = _run_cli("--input-json", str(tmp_path / "nope.json"), "--output-snapshot", snap_path)
        assert result.returncode == 1

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        report_path = _write_report(tmp_path / "report.json", _make_correct_report())
        snap_path = str(tmp_path / "sub" / "dir" / "snap.json")
        result = _run_cli("--input-json", report_path, "--output-snapshot", snap_path)
        assert result.returncode == 0
        assert Path(snap_path).exists()
