"""Tests for task queue compatibility — T961-T1060 entries present."""
from __future__ import annotations

import pathlib
import pytest

_QUEUE_PATH = pathlib.Path(__file__).resolve().parent.parent.parent / "docs" / "dev_prd" / "runtime_governance_task_queue.md"


class TestTaskQueueCompatibility:
    def test_queue_contains_t961_t1060(self):
        """Verify task queue doc references T961 and T1060."""
        text = _QUEUE_PATH.read_text(encoding="utf-8")
        assert "T961" in text, "T961 not found in task queue"
        assert "T1060" in text, "T1060 not found in task queue"

    def test_queue_t1061_human_review(self):
        """Verify T1061+ requires human review."""
        text = _QUEUE_PATH.read_text(encoding="utf-8")
        assert "T1061" in text, "T1061 not found in task queue"
        assert "HUMAN_REVIEW_REQUIRED" in text, "HUMAN_REVIEW_REQUIRED not found in task queue"

    def test_release_hold_still_hold(self):
        """Verify release hold is still HOLD."""
        text = _QUEUE_PATH.read_text(encoding="utf-8")
        assert "Release hold: HOLD" in text, "Release hold not HOLD"
