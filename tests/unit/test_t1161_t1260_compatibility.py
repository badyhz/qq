from __future__ import annotations

from pathlib import Path

import pytest

TASK_QUEUE_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "dev_prd" / "runtime_governance_task_queue.md"


@pytest.fixture()
def task_queue_text() -> str:
    assert TASK_QUEUE_PATH.exists(), f"Task queue doc not found: {TASK_QUEUE_PATH}"
    return TASK_QUEUE_PATH.read_text(encoding="utf-8")


class TestT1161T1260Compatibility:
    def test_doc_exists(self) -> None:
        assert TASK_QUEUE_PATH.exists()

    def test_contains_t1161(self, task_queue_text: str) -> None:
        assert "T1161" in task_queue_text

    def test_contains_t1260(self, task_queue_text: str) -> None:
        assert "T1260" in task_queue_text

    def test_contains_range_entries(self, task_queue_text: str) -> None:
        for tid in ("T1161", "T1170", "T1180"):
            assert tid in task_queue_text, f"{tid} not found in task queue doc"
