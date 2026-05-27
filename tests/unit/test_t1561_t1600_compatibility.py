"""Compatibility tests for T1561-T1600 frozen backlog review report CLI batch."""
from __future__ import annotations

import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_QUEUE_PATH = _ROOT / "docs" / "dev_prd" / "runtime_governance_task_queue.md"
_STATE_PATH = _ROOT / "docs" / "dev_prd" / "runtime_governance_current_state.md"
_DOCS_DIR = _ROOT / "docs" / "dev_prd"


class TestTaskQueueContainsT1521:
    """Verify task_queue doc references T1521-T1600 range."""

    def test_queue_contains_t1521(self):
        text = _QUEUE_PATH.read_text(encoding="utf-8")
        assert "T1521" in text, "T1521 not found in task queue"

    def test_queue_contains_t1600(self):
        text = _QUEUE_PATH.read_text(encoding="utf-8")
        assert "T1600" in text, "T1600 not found in task queue"

    def test_queue_release_hold_is_hold(self):
        text = _QUEUE_PATH.read_text(encoding="utf-8")
        assert "Release hold: HOLD" in text, "Release hold not HOLD"


class TestCurrentStateUpdated:
    """Verify current_state doc includes CLI/report materializer section."""

    def test_state_contains_frozen_backlog_review_report_cli(self):
        text = _STATE_PATH.read_text(encoding="utf-8")
        assert "Frozen Backlog Review Report CLI" in text, "CLI section not in current state"

    def test_state_contains_materializer(self):
        text = _STATE_PATH.read_text(encoding="utf-8")
        assert "materializer" in text.lower(), "materializer not in current state"


class TestCloseoutDocsExist:
    """Verify all T1561-T1600 closeout docs exist."""

    @pytest.mark.parametrize(
        "filename",
        [
            "frozen_backlog_review_report_cli.md",
            "frozen_backlog_review_report_materializer.md",
            "t1521_t1600_acceptance_packet.md",
            "t1521_t1600_safety_boundary_packet.md",
            "t1521_t1600_final_closeout_report.md",
        ],
    )
    def test_doc_exists(self, filename: str):
        path = _DOCS_DIR / filename
        assert path.exists(), f"{filename} does not exist at {path}"


class TestSafetyBoundaryPacketContent:
    """Verify safety boundary packet references frozen files."""

    def test_safety_packet_has_frozen_files(self):
        path = _DOCS_DIR / "t1521_t1600_safety_boundary_packet.md"
        text = path.read_text(encoding="utf-8")
        assert "live_runner.py" in text, "live_runner.py not in safety packet"
        assert "HOLD" in text, "HOLD not in safety packet"
