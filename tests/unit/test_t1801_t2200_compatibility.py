"""T1801-T2200 Acceptance Compatibility Tests.

Verify that all acceptance documentation, task queue references,
current state references, safety invariants, and HUMAN_REVIEW_REQUIRED
markers are in place for the T1801-T2200 Frozen Backlog Review Platform v1.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent.parent
_DEV_PRD = _REPO / "docs" / "dev_prd"


class TestAcceptanceDocsExist:
    """Verify all T1801-T2200 acceptance docs exist."""

    def test_acceptance_packet_exists(self):
        path = _DEV_PRD / "t1801_t2200_acceptance_packet.md"
        assert path.exists(), f"Missing: {path}"

    def test_safety_boundary_packet_exists(self):
        path = _DEV_PRD / "t1801_t2200_safety_boundary_packet.md"
        assert path.exists(), f"Missing: {path}"

    def test_platform_closeout_report_exists(self):
        path = _DEV_PRD / "t1801_t2200_platform_closeout_report.md"
        assert path.exists(), f"Missing: {path}"

    def test_platform_index_exists(self):
        path = _DEV_PRD / "frozen_backlog_review_platform_index.md"
        assert path.exists(), f"Missing: {path}"


class TestTaskQueueReferences:
    """Verify task queue references T1801 and T2200."""

    def _read_task_queue(self) -> str:
        path = _DEV_PRD / "runtime_governance_task_queue.md"
        assert path.exists(), "Task queue doc missing"
        return path.read_text(encoding="utf-8")

    def test_task_queue_references_t1801(self):
        content = self._read_task_queue()
        assert "T1801" in content, "Task queue does not reference T1801"

    def test_task_queue_references_t2200(self):
        content = self._read_task_queue()
        assert "T2200" in content, "Task queue does not reference T2200"

    def test_task_queue_references_completed(self):
        content = self._read_task_queue()
        assert "T1801-T2200" in content, "Task queue does not reference T1801-T2200 completed range"


class TestCurrentStateReferences:
    """Verify current state references platform."""

    def _read_current_state(self) -> str:
        path = _DEV_PRD / "runtime_governance_current_state.md"
        assert path.exists(), "Current state doc missing"
        return path.read_text(encoding="utf-8")

    def test_current_state_references_platform(self):
        content = self._read_current_state()
        assert "T1801-T2200" in content, "Current state does not reference T1801-T2200"

    def test_current_state_references_frozen_backlog(self):
        content = self._read_current_state()
        assert "frozen backlog" in content.lower(), (
            "Current state does not reference frozen backlog"
        )


class TestReleaseHoldStillHOLD:
    """Verify release_hold=HOLD in docs."""

    def _read_doc(self, name: str) -> str:
        path = _DEV_PRD / name
        assert path.exists(), f"Missing: {name}"
        return path.read_text(encoding="utf-8")

    def test_acceptance_packet_hold(self):
        content = self._read_doc("t1801_t2200_acceptance_packet.md")
        assert "HOLD" in content, "Acceptance packet missing HOLD"

    def test_safety_boundary_hold(self):
        content = self._read_doc("t1801_t2200_safety_boundary_packet.md")
        assert "HOLD" in content, "Safety boundary missing HOLD"

    def test_closeout_hold(self):
        content = self._read_doc("t1801_t2200_platform_closeout_report.md")
        assert "HOLD" in content, "Closeout report missing HOLD"

    def test_task_queue_hold(self):
        content = self._read_doc("runtime_governance_task_queue.md")
        assert "HOLD" in content, "Task queue missing HOLD"

    def test_current_state_hold(self):
        content = self._read_doc("runtime_governance_current_state.md")
        assert "HOLD" in content, "Current state missing HOLD"


class TestHumanReviewRequired:
    """Verify HUMAN_REVIEW_REQUIRED mentioned for T2201+."""

    def _read_doc(self, name: str) -> str:
        path = _DEV_PRD / name
        assert path.exists(), f"Missing: {name}"
        return path.read_text(encoding="utf-8")

    def test_closeout_mentions_human_review(self):
        content = self._read_doc("t1801_t2200_platform_closeout_report.md")
        assert "HUMAN_REVIEW_REQUIRED" in content, (
            "Closeout does not mention HUMAN_REVIEW_REQUIRED"
        )

    def test_task_queue_mentions_human_review(self):
        content = self._read_doc("runtime_governance_task_queue.md")
        assert "HUMAN_REVIEW_REQUIRED" in content, (
            "Task queue does not mention HUMAN_REVIEW_REQUIRED"
        )

    def test_current_state_mentions_human_review(self):
        content = self._read_doc("runtime_governance_current_state.md")
        assert "HUMAN_REVIEW_REQUIRED" in content, (
            "Current state does not mention HUMAN_REVIEW_REQUIRED"
        )
