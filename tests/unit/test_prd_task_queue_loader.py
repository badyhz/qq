"""Tests for PRD task queue loader — T866."""

from pathlib import Path

from core.prd_task_queue_loader import (
    extract_task_ids_from_markdown,
    find_task_section,
    load_prd_task_queue_from_markdown,
    task_queue_loader_summary,
)

SAMPLE_MD = """\
# Task Queue

## Completed Ranges

- T786-T789: governance failure reporting — completed
- T790-T793: governance support stack — completed

## Current Phase

- T858: setup alpha — in_progress
- T859: setup beta — in_progress

## Next Queue

- T865: PRD-driven task loader spec
- T866: PRD task queue validator
- T867: agent prompt generator
- T868: PRD acceptance command registry
- T869: PRD safety boundary checker
- T870: PRD execution report parser
- T871: PRD queue closeout packet
- T872: PRD control plane final status report

## Notes

Some extra text referencing T865 again for duplication test.
"""


def test_extract_task_ids():
    ids = extract_task_ids_from_markdown(SAMPLE_MD)
    # extract_task_ids_from_markdown is regex-based, does NOT expand ranges
    # Ranges like T786-T789 yield only T786 and T789
    assert ids == [
        "T786", "T789",
        "T790", "T793",
        "T858", "T859",
        "T865", "T866", "T867", "T868", "T869", "T870", "T871", "T872",
    ]


def test_extract_task_ids_no_duplicates():
    ids = extract_task_ids_from_markdown(SAMPLE_MD)
    assert len(ids) == len(set(ids)), "duplicate task IDs found"


def test_load_tasks_count():
    tasks = load_prd_task_queue_from_markdown(SAMPLE_MD)
    # T786-T789=4, T790-T793=4, T858=1, T859=1, T865-T872=8, duplicate T865 skipped
    assert len(tasks) == 18


def test_load_tasks_ids():
    tasks = load_prd_task_queue_from_markdown(SAMPLE_MD)
    ids = [t.task_id for t in tasks]
    for expected in ["T865", "T866", "T867", "T868", "T869", "T870", "T871", "T872"]:
        assert expected in ids, f"{expected} missing"


def test_load_completed_status():
    tasks = load_prd_task_queue_from_markdown(SAMPLE_MD)
    completed = [t for t in tasks if t.status == "COMPLETED"]
    completed_ids = {t.task_id for t in completed}
    assert "T786" in completed_ids
    assert "T793" in completed_ids


def test_load_not_started_status():
    tasks = load_prd_task_queue_from_markdown(SAMPLE_MD)
    not_started = [t for t in tasks if t.status == "NOT_STARTED"]
    not_started_ids = {t.task_id for t in not_started}
    assert "T865" in not_started_ids
    assert "T872" in not_started_ids


def test_load_defaults():
    tasks = load_prd_task_queue_from_markdown(SAMPLE_MD)
    t865 = [t for t in tasks if t.task_id == "T865"][0]
    assert t865.allowed_files == []
    assert t865.dependencies == []
    assert t865.acceptance_commands == []
    assert t865.risk_level == "MEDIUM"
    assert "loaded_from_markdown" in t865.notes


def test_load_deduplicates():
    tasks = load_prd_task_queue_from_markdown(SAMPLE_MD)
    ids = [t.task_id for t in tasks]
    assert ids.count("T865") == 1, "T865 should appear only once"


def test_load_deterministic():
    t1 = load_prd_task_queue_from_markdown(SAMPLE_MD)
    t2 = load_prd_task_queue_from_markdown(SAMPLE_MD)
    assert t1 == t2


def test_find_task_section():
    section = find_task_section(SAMPLE_MD, "T865")
    assert "## Next Queue" in section
    assert "T865" in section
    assert "T872" in section


def test_find_task_section_unknown():
    section = find_task_section(SAMPLE_MD, "T999")
    assert section == ""


def test_find_task_section_invalid_id():
    section = find_task_section(SAMPLE_MD, "INVALID")
    assert section == ""


def test_summary():
    tasks = load_prd_task_queue_from_markdown(SAMPLE_MD)
    summary = task_queue_loader_summary(tasks)
    assert summary["total"] == 18
    assert summary["status_counts"]["COMPLETED"] == 8
    assert summary["status_counts"]["NOT_STARTED"] == 10
    assert summary["risk_counts"]["MEDIUM"] == 18


def test_runtime_governance_task_queue_has_t865_t872():
    """Verify docs/dev_prd/runtime_governance_task_queue.md includes T865-T872."""
    path = Path(__file__).resolve().parents[2] / "docs" / "dev_prd" / "runtime_governance_task_queue.md"
    text = path.read_text()
    ids = extract_task_ids_from_markdown(text)
    for expected in ["T865", "T866", "T867", "T868", "T869", "T870", "T871", "T872"]:
        assert expected in ids, f"{expected} missing from runtime_governance_task_queue.md"


def test_table_row_format():
    md = "| T900 | some title | NOT_STARTED |\n| T901 | other title | completed |\n"
    tasks = load_prd_task_queue_from_markdown(md)
    assert len(tasks) == 2
    assert tasks[0].task_id == "T900"
    assert tasks[0].title == "some title"
    assert tasks[1].status == "COMPLETED"
