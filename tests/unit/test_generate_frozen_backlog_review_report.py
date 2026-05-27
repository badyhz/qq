"""T1533 - Tests for frozen backlog review report CLI.

Runs the CLI via subprocess. Validates output files.
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
    / "generate_frozen_backlog_review_report.py"
)


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, _SCRIPT, *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


# --- T1533: CLI output tests ---


class TestCLIOutput:
    """Tests for CLI output generation."""

    def test_exit_code_zero_with_md_and_json(self, tmp_path: Path) -> None:
        md_path = str(tmp_path / "report.md")
        json_path = str(tmp_path / "report.json")
        result = _run_cli("--output-md", md_path, "--output-json", json_path)
        assert result.returncode == 0, result.stderr

    def test_md_file_exists(self, tmp_path: Path) -> None:
        md_path = str(tmp_path / "report.md")
        json_path = str(tmp_path / "report.json")
        _run_cli("--output-md", md_path, "--output-json", json_path)
        assert Path(md_path).exists()

    def test_json_file_exists(self, tmp_path: Path) -> None:
        md_path = str(tmp_path / "report.md")
        json_path = str(tmp_path / "report.json")
        _run_cli("--output-md", md_path, "--output-json", json_path)
        assert Path(json_path).exists()

    def test_md_contains_hold_and_22(self, tmp_path: Path) -> None:
        md_path = str(tmp_path / "report.md")
        _run_cli("--output-md", md_path, "--output-json", str(tmp_path / "r.json"))
        content = Path(md_path).read_text()
        assert "HOLD" in content
        assert "22" in content

    def test_json_valid_and_has_summary_counts(self, tmp_path: Path) -> None:
        json_path = str(tmp_path / "report.json")
        _run_cli("--output-md", str(tmp_path / "r.md"), "--output-json", json_path)
        data = json.loads(Path(json_path).read_text())
        assert data["summary"]["total_files"] == 22
        assert data["summary"]["high_risk_count"] == 9
        assert data["summary"]["medium_risk_count"] == 13
        assert data["summary"]["release_hold"] == "HOLD"

    def test_mode_full_produces_per_file_sections(self, tmp_path: Path) -> None:
        md_path = str(tmp_path / "report.md")
        _run_cli("--output-md", md_path, "--mode", "full")
        content = Path(md_path).read_text()
        assert "core/live_runner.py" in content
        assert "scripts/live_playbook.py" in content
        assert "Frozen Files" in content

    def test_mode_summary_produces_summary_only(self, tmp_path: Path) -> None:
        md_path = str(tmp_path / "report.md")
        _run_cli("--output-md", md_path, "--mode", "summary")
        content = Path(md_path).read_text()
        assert "Summary" in content
        # Summary-only should not contain per-file section headers
        assert "Frozen Files" not in content

    def test_mode_full_json_has_records(self, tmp_path: Path) -> None:
        json_path = str(tmp_path / "report.json")
        _run_cli("--output-json", json_path, "--mode", "full")
        data = json.loads(Path(json_path).read_text())
        assert "records" in data
        assert len(data["records"]) == 22

    def test_mode_summary_json_has_no_records(self, tmp_path: Path) -> None:
        json_path = str(tmp_path / "report.json")
        _run_cli("--output-json", json_path, "--mode", "summary")
        data = json.loads(Path(json_path).read_text())
        assert "records" not in data
        assert "summary" in data

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        md_path = str(tmp_path / "sub" / "dir" / "report.md")
        _run_cli("--output-md", md_path)
        assert Path(md_path).exists()

    def test_exit_code_1_with_no_output_args(self, tmp_path: Path) -> None:
        result = _run_cli()
        assert result.returncode == 1

    def test_stdout_contains_confirmation(self, tmp_path: Path) -> None:
        md_path = str(tmp_path / "report.md")
        result = _run_cli("--output-md", md_path)
        assert "Markdown report written" in result.stdout
