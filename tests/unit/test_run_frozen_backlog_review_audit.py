"""T1626 - Tests for run_frozen_backlog_review_audit.py orchestrator CLI.

Runs the CLI via subprocess. Validates outputs.
No network. No live. No submit.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = str(
    Path(__file__).resolve().parent.parent.parent
    / "scripts"
    / "run_frozen_backlog_review_audit.py"
)


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, _SCRIPT, *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


class TestAuditOrchestrator:
    """Tests for the frozen backlog review audit orchestrator."""

    def test_full_mode_creates_all_outputs(self, tmp_path: Path) -> None:
        result = _run_cli("--output-dir", str(tmp_path), "--mode", "full")
        assert result.returncode == 0
        assert (tmp_path / "frozen_backlog_review.md").exists()
        assert (tmp_path / "frozen_backlog_review.json").exists()
        assert (tmp_path / "frozen_backlog_validation.txt").exists()
        assert (tmp_path / "frozen_backlog_audit_summary.md").exists()

    def test_summary_mode_creates_all_outputs(self, tmp_path: Path) -> None:
        # Summary mode JSON has no records, so validation FAIL is expected
        result = _run_cli("--output-dir", str(tmp_path), "--mode", "summary")
        assert (tmp_path / "frozen_backlog_review.md").exists()
        assert (tmp_path / "frozen_backlog_review.json").exists()
        assert (tmp_path / "frozen_backlog_validation.txt").exists()
        assert (tmp_path / "frozen_backlog_audit_summary.md").exists()
        assert "Mode: summary" in result.stdout

    def test_validation_output_contains_pass(self, tmp_path: Path) -> None:
        result = _run_cli("--output-dir", str(tmp_path))
        assert result.returncode == 0
        val_content = (tmp_path / "frozen_backlog_validation.txt").read_text()
        assert "PASS" in val_content

    def test_audit_summary_exists_and_has_content(self, tmp_path: Path) -> None:
        result = _run_cli("--output-dir", str(tmp_path))
        assert result.returncode == 0
        summary_path = tmp_path / "frozen_backlog_audit_summary.md"
        assert summary_path.exists()
        content = summary_path.read_text()
        assert "Frozen Backlog Audit Summary" in content
        assert "PASS" in content

    def test_stdout_contains_deterministic_summary(self, tmp_path: Path) -> None:
        result = _run_cli("--output-dir", str(tmp_path))
        assert result.returncode == 0
        assert "Mode: full" in result.stdout
        assert "Files: 22" in result.stdout
        assert "Validation: PASS" in result.stdout

    def test_json_report_is_valid_json(self, tmp_path: Path) -> None:
        result = _run_cli("--output-dir", str(tmp_path))
        assert result.returncode == 0
        json_path = tmp_path / "frozen_backlog_review.json"
        data = json.loads(json_path.read_text())
        assert "summary" in data
        assert "records" in data
        assert data["summary"]["total_files"] == 22
        assert data["summary"]["release_hold"] == "HOLD"

    def test_diff_same_report_no_changes(self, tmp_path: Path) -> None:
        # Generate a report first
        first_run = tmp_path / "first"
        result = _run_cli("--output-dir", str(first_run))
        assert result.returncode == 0

        # Use that report as snapshot for a second run
        snapshot_path = first_run / "frozen_backlog_review.json"
        second_run = tmp_path / "second"
        result = _run_cli(
            "--output-dir", str(second_run),
            "--snapshot", str(snapshot_path),
        )
        assert result.returncode == 0
        assert (second_run / "frozen_backlog_diff.md").exists()
        assert (second_run / "frozen_backlog_diff.json").exists()

        diff_data = json.loads((second_run / "frozen_backlog_diff.json").read_text())
        assert diff_data["has_changes"] is False
        assert diff_data["total_changes"] == 0

    def test_diff_shows_no_changes_in_stdout(self, tmp_path: Path) -> None:
        first_run = tmp_path / "first"
        _run_cli("--output-dir", str(first_run))
        snapshot_path = first_run / "frozen_backlog_review.json"
        second_run = tmp_path / "second"
        result = _run_cli(
            "--output-dir", str(second_run),
            "--snapshot", str(snapshot_path),
        )
        assert result.returncode == 0
        assert "Diff has changes: False" in result.stdout

    def test_diff_with_missing_snapshot_exits_one(self, tmp_path: Path) -> None:
        result = _run_cli(
            "--output-dir", str(tmp_path),
            "--snapshot", str(tmp_path / "nonexistent.json"),
        )
        assert result.returncode == 1

    def test_output_dir_created_if_missing(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "c"
        result = _run_cli("--output-dir", str(nested))
        assert result.returncode == 0
        assert nested.exists()
        assert (nested / "frozen_backlog_review.json").exists()
