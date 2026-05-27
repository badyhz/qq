"""T1624 - Tests for diff_frozen_backlog_review_reports.py CLI.

Runs the CLI via subprocess. Validates diff output.
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
    / "diff_frozen_backlog_review_reports.py"
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


class TestDiffCLI:
    """Tests for the diff CLI script."""

    def test_diff_same_file_no_changes(self, tmp_path: Path) -> None:
        report_path = _write_report(tmp_path / "report.json", _make_correct_report())
        result = _run_cli("--before-json", report_path, "--after-json", report_path)
        assert result.returncode == 0
        assert "Changes detected: False" in result.stdout
        assert "Total changes: 0" in result.stdout

    def test_diff_with_modified_field(self, tmp_path: Path) -> None:
        before_path = _write_report(tmp_path / "before.json", _make_correct_report())
        after_data = _make_correct_report()
        after_data["records"][0]["risk_class"] = "MEDIUM"
        after_path = _write_report(tmp_path / "after.json", after_data)
        result = _run_cli("--before-json", before_path, "--after-json", after_path)
        assert result.returncode == 0
        assert "Changes detected: True" in result.stdout
        assert "Field changes: 1" in result.stdout

    def test_diff_writes_markdown(self, tmp_path: Path) -> None:
        before_path = _write_report(tmp_path / "before.json", _make_correct_report())
        after_path = _write_report(tmp_path / "after.json", _make_correct_report())
        md_path = str(tmp_path / "diff.md")
        result = _run_cli(
            "--before-json", before_path,
            "--after-json", after_path,
            "--output-md", md_path,
        )
        assert result.returncode == 0
        assert Path(md_path).exists()
        content = Path(md_path).read_text()
        assert "Frozen Backlog Diff Report" in content
        assert "No changes detected" in content

    def test_diff_writes_json(self, tmp_path: Path) -> None:
        before_path = _write_report(tmp_path / "before.json", _make_correct_report())
        after_data = _make_correct_report()
        after_data["summary"]["release_hold"] = "RELEASED"
        after_path = _write_report(tmp_path / "after.json", after_data)
        json_path = str(tmp_path / "diff.json")
        result = _run_cli(
            "--before-json", before_path,
            "--after-json", after_path,
            "--output-json", json_path,
        )
        assert result.returncode == 0
        assert Path(json_path).exists()
        data = json.loads(Path(json_path).read_text())
        assert data["has_changes"] is True
        assert len(data["summary_changes"]) > 0

    def test_diff_missing_before_exit_one(self, tmp_path: Path) -> None:
        after_path = _write_report(tmp_path / "after.json", _make_correct_report())
        result = _run_cli(
            "--before-json", str(tmp_path / "nope.json"),
            "--after-json", after_path,
        )
        assert result.returncode == 1

    def test_diff_stdout_contains_summary(self, tmp_path: Path) -> None:
        before_path = _write_report(tmp_path / "before.json", _make_correct_report())
        after_path = _write_report(tmp_path / "after.json", _make_correct_report())
        result = _run_cli("--before-json", before_path, "--after-json", after_path)
        assert "Added files:" in result.stdout
        assert "Removed files:" in result.stdout
        assert "Summary changes:" in result.stdout

    def test_diff_with_added_record(self, tmp_path: Path) -> None:
        before = _make_correct_report()
        before_path = _write_report(tmp_path / "before.json", before)
        after = _make_correct_report()
        extra = copy.deepcopy(_CORRECT_RECORD_TEMPLATE)
        extra["file_path"] = "extra/new_file.py"
        extra["record_id"] = "report-0099"
        after["records"].append(extra)
        after_path = _write_report(tmp_path / "after.json", after)
        result = _run_cli("--before-json", before_path, "--after-json", after_path)
        assert result.returncode == 0
        assert "Changes detected: True" in result.stdout
