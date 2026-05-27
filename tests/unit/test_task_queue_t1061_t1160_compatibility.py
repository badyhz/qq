from __future__ import annotations

from pathlib import Path

import pytest

QUEUE = Path("docs/dev_prd/runtime_governance_task_queue.md")


def _read_queue() -> str:
    return QUEUE.read_text(encoding="utf-8")


def test_task_queue_doc_exists() -> None:
    assert QUEUE.exists(), f"Missing: {QUEUE}"


T1061_TO_T1080 = [f"T{t}" for t in range(1061, 1081)]


@pytest.mark.parametrize("task_id", T1061_TO_T1080)
def test_t1061_to_t1080_entries_present(task_id: str) -> None:
    text = _read_queue()
    assert task_id in text, f"Task {task_id} not found in task queue"


T1081_TO_T1160_RANGE_REFS = [
    "T1081-T1110",
    "T1111-T1120",
    "T1121-T1140",
    "T1141-T1160",
]


@pytest.mark.parametrize("range_ref", T1081_TO_T1160_RANGE_REFS)
def test_t1081_to_t1160_range_references_present(range_ref: str) -> None:
    text = _read_queue()
    assert range_ref in text, f"Range {range_ref} not found in task queue"
