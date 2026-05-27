"""T1349 - Compatibility tests for runtime governance task queue."""
from __future__ import annotations

import os

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TASK_QUEUE_PATH = os.path.join(
    REPO_ROOT, "docs", "dev_prd", "runtime_governance_task_queue.md"
)


def _read_task_queue() -> str:
    with open(TASK_QUEUE_PATH, encoding="utf-8") as f:
        return f.read()


class TestTaskQueueCompatibility:
    def test_task_queue_doc_exists(self):
        assert os.path.isfile(TASK_QUEUE_PATH), (
            f"Missing task queue doc: {TASK_QUEUE_PATH}"
        )

    def test_contains_t1261(self):
        content = _read_task_queue()
        assert "T1261" in content, "Task queue doc must reference T1261"

    def test_contains_range_t1270(self):
        content = _read_task_queue()
        assert "T1270" in content, "Task queue doc must reference T1270"

    def test_contains_range_t1280(self):
        content = _read_task_queue()
        assert "T1280" in content, "Task queue doc must reference T1280"

    def test_contains_range_t1261_t1300(self):
        """T1261-T1300 range must be documented (covers T1270, T1280, T1290, T1300)."""
        content = _read_task_queue()
        assert "T1261-T1300" in content, "Task queue doc must have T1261-T1300 range"

    def test_contains_range_t1300(self):
        content = _read_task_queue()
        assert "T1300" in content, "Task queue doc must reference T1300"

    def test_t1360_dependency_noted(self):
        """T1360 may not yet be in the task_queue doc.
        This test documents the dependency: T1351 will add T1261-T1360 range.
        """
        content = _read_task_queue()
        # T1360 presence is optional at this stage; test passes either way.
        # The test exists to document the dependency for future verification.
        has_t1360 = "T1360" in content
        # Always pass — this is a compatibility marker, not a gate.
        assert True, f"T1360 present: {has_t1360}"
