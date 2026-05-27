"""T1535 - Compatibility tests for T1532-T1560 frozen backlog review report CLI.

Verifies file existence, model importability, and release_hold = HOLD.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestT1532T1560Compatibility:
    """Compatibility checks for the CLI and report models."""

    def test_cli_script_exists(self) -> None:
        script = _REPO_ROOT / "scripts" / "generate_frozen_backlog_review_report.py"
        assert script.exists(), f"CLI script not found: {script}"

    def test_report_models_importable(self) -> None:
        from core.frozen_backlog_report_summary import FrozenBacklogReportSummary
        from core.frozen_backlog_report_record import FrozenBacklogReportRecord
        from core.frozen_backlog_report_materializer import materialize_full_report
        from core.frozen_backlog_report_renderer import render_report_markdown
        from core.frozen_backlog_report_json import render_report_json

        assert FrozenBacklogReportSummary is not None
        assert FrozenBacklogReportRecord is not None
        assert callable(materialize_full_report)
        assert callable(render_report_markdown)
        assert callable(render_report_json)

    def test_release_hold_is_hold(self) -> None:
        from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY

        inventory = FROZEN_BACKLOG_INVENTORY
        for rec in inventory.records:
            assert rec.release_hold == "HOLD", f"{rec.file_path} release_hold != HOLD"

    def test_inventory_has_22_records(self) -> None:
        from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY

        inventory = FROZEN_BACKLOG_INVENTORY
        assert inventory.total_count == 22
        assert len(inventory.records) == 22

    def test_materializer_produces_summary_and_records(self) -> None:
        from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY
        from core.frozen_backlog_report_materializer import materialize_full_report

        inventory = FROZEN_BACKLOG_INVENTORY
        summary, records = materialize_full_report(inventory)
        assert summary.total_files == 22
        assert len(records) == 22
        assert summary.release_hold == "HOLD"
