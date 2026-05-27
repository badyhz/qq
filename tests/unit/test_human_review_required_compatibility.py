from __future__ import annotations

from pathlib import Path

QUEUE = Path("docs/dev_prd/runtime_governance_task_queue.md")


def _read() -> str:
    return QUEUE.read_text(encoding="utf-8")


def test_queue_doc_exists() -> None:
    assert QUEUE.exists()


T1061_TO_T1080 = [f"T{t}" for t in range(1061, 1081)]


def test_t1061_t1080_all_marked_human_review_required() -> None:
    text = _read()
    for task_id in T1061_TO_T1080:
        assert task_id in text, f"{task_id} missing from task queue"
    assert text.count("HUMAN_REVIEW_REQUIRED") >= 20


def test_human_review_required_count() -> None:
    text = _read()
    count = text.count("HUMAN_REVIEW_REQUIRED")
    assert count >= 20, f"Expected >=20 HUMAN_REVIEW_REQUIRED, found {count}"


def test_no_autonomous_progression_note() -> None:
    text = _read().lower()
    assert "no autonomous progression" in text or "require human review" in text


def test_t1061_through_t1080_present_in_queue() -> None:
    text = _read()
    present = [t for t in T1061_TO_T1080 if t in text]
    assert len(present) == 20, f"Expected 20 tasks, found {len(present)}: {present}"
