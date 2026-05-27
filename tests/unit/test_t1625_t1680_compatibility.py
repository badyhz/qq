"""T1627 - Compatibility tests for T1625-T1680 batch.

Verifies: orchestrator script exists, all CLIs importable,
22 frozen files still untracked, release_hold is HOLD.
No network. No live. No submit.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

_FROZEN_SCRIPTS = [
    "scripts/run_frozen_backlog_review_audit.py",
    "scripts/generate_frozen_backlog_review_report.py",
    "scripts/validate_frozen_backlog_review_report.py",
    "scripts/snapshot_frozen_backlog_review_report.py",
    "scripts/diff_frozen_backlog_review_reports.py",
]


class TestT1625T1680Compatibility:
    """Compatibility checks for the frozen backlog review audit suite."""

    def test_orchestrator_script_exists(self) -> None:
        script = _REPO_ROOT / "scripts" / "run_frozen_backlog_review_audit.py"
        assert script.exists(), f"Missing: {script}"

    def test_all_clis_importable(self) -> None:
        """Verify all frozen backlog review CLIs can be imported."""
        for script_rel in _FROZEN_SCRIPTS:
            script_path = _REPO_ROOT / script_rel
            assert script_path.exists(), f"Missing CLI: {script_rel}"

            result = subprocess.run(
                [sys.executable, "-c", f"import importlib.util; "
                 f"spec = importlib.util.spec_from_file_location('mod', '{script_path}'); "
                 f"mod = importlib.util.module_from_spec(spec); "
                 f"spec.loader.exec_module(mod)"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0, (
                f"Import failed for {script_rel}: {result.stderr}"
            )

    def test_frozen_backlog_inventory_has_22_files(self) -> None:
        """Verify the frozen inventory contains exactly 22 records."""
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, '.'); "
             "from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY; "
             "print(FROZEN_BACKLOG_INVENTORY.total_count)"],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            timeout=30,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "22"

    def test_release_hold_is_hold(self) -> None:
        """Verify release_hold is HOLD across all inventory records."""
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, '.'); "
             "from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY; "
             "holds = [r.release_hold for r in FROZEN_BACKLOG_INVENTORY.records]; "
             "print(all(h == 'HOLD' for h in holds))"],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            timeout=30,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "True"

    def test_frozen_files_still_untracked(self) -> None:
        """Verify the 22 frozen files remain untracked by git."""
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            timeout=15,
        )
        assert result.returncode == 0
        untracked = set(result.stdout.strip().splitlines())

        from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY
        frozen_paths = {r.file_path for r in FROZEN_BACKLOG_INVENTORY.records}
        tracked_frozen = frozen_paths & set(
            subprocess.run(
                ["git", "ls-files"],
                capture_output=True,
                text=True,
                cwd=str(_REPO_ROOT),
                timeout=15,
            ).stdout.strip().splitlines()
        )
        # Frozen files should NOT be tracked
        assert len(tracked_frozen) == 0, (
            f"Frozen files unexpectedly tracked: {tracked_frozen}"
        )
