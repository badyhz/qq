"""Tests for T1601-T1800 frozen backlog review automation suite compatibility."""
from __future__ import annotations

import pathlib

_QUEUE_PATH = pathlib.Path(__file__).resolve().parent.parent.parent / "docs" / "dev_prd" / "runtime_governance_task_queue.md"
_STATE_PATH = pathlib.Path(__file__).resolve().parent.parent.parent / "docs" / "dev_prd" / "runtime_governance_current_state.md"
_DEV_PRD_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "docs" / "dev_prd"


class TestT1681T1800Compatibility:

    def test_queue_contains_t1601(self):
        """Verify task queue doc references T1601-T1800 completed range."""
        text = _QUEUE_PATH.read_text(encoding="utf-8")
        assert "T1601" in text, "T1601 not found in task queue"
        assert "T1800" in text, "T1800 not found in task queue"

    def test_current_state_updated(self):
        """Verify current state doc has automation suite section."""
        text = _STATE_PATH.read_text(encoding="utf-8")
        assert "T1601-T1800" in text, "T1601-T1800 not found in current state"
        assert "automation" in text.lower() or "frozen backlog" in text.lower(), \
            "Automation suite section not found in current state"

    def test_closeout_docs_exist(self):
        """Verify all 7 closeout docs exist."""
        required = [
            "frozen_backlog_report_validator.md",
            "frozen_backlog_report_snapshot.md",
            "frozen_backlog_report_diff.md",
            "frozen_backlog_review_audit_cli.md",
            "t1601_t1800_acceptance_packet.md",
            "t1601_t1800_safety_boundary_packet.md",
            "t1601_t1800_final_closeout_report.md",
        ]
        for name in required:
            path = _DEV_PRD_DIR / name
            assert path.exists(), f"Missing doc: {name}"

    def test_release_hold_still_hold(self):
        """Verify release hold is still HOLD in task queue."""
        text = _QUEUE_PATH.read_text(encoding="utf-8")
        assert "HOLD" in text, "Release hold not HOLD in task queue"

    def test_validator_doc_has_rules(self):
        """Verify validator doc contains validation rules."""
        path = _DEV_PRD_DIR / "frozen_backlog_report_validator.md"
        text = path.read_text(encoding="utf-8")
        assert "Structural Validation" in text, "Structural Validation section missing"
        assert "Completeness Validation" in text, "Completeness Validation section missing"
        assert "Policy Compliance" in text, "Policy Compliance section missing"
