"""Tests for prd_500_backlog_milestone_map — T905.

Deterministic. No I/O. No timestamps. No random.
"""

from core.prd_backlog_schema import PrdBacklog, PrdBacklogItem
from core.prd_500_backlog_milestone_map import (
    Prd500MilestoneMapEntry,
    build_prd_500_milestone_map,
    milestone_map_to_dict,
    milestone_map_to_markdown,
    summarize_milestone_map,
)


def _item(task_id: str, milestone_id: str, risk: str = "LOW", status: str = "NOT_STARTED") -> PrdBacklogItem:
    return PrdBacklogItem(
        task_id=task_id,
        title=f"task {task_id}",
        milestone_id=milestone_id,
        wave_id="W1",
        batch_id="B1",
        risk_level=risk,
        status=status,
        dependencies=[],
        allowed_file_patterns=[],
        forbidden_file_patterns=[],
        acceptance_command_ids=[],
        notes=[],
    )


def _backlog(items):
    return PrdBacklog(
        backlog_id="TEST-BL",
        items=items,
        total_expected_tasks=len(items),
        status="NOT_STARTED",
        notes=[],
    )


class TestMilestoneMap:
    def test_map_covers_all_items(self):
        """sum of task_count == len(backlog.items)"""
        items = [
            _item("T1", "M1"),
            _item("T2", "M1"),
            _item("T3", "M2"),
            _item("T4", "M2"),
            _item("T5", "M2"),
        ]
        bl = _backlog(items)
        entries = build_prd_500_milestone_map(bl)
        total = sum(e.task_count for e in entries)
        assert total == len(items)

    def test_ordered(self):
        """milestone_ids appear in first-seen order."""
        items = [
            _item("T10", "M_BETA"),
            _item("T11", "M_ALPHA"),
            _item("T12", "M_BETA"),
        ]
        bl = _backlog(items)
        entries = build_prd_500_milestone_map(bl)
        ids = [e.milestone_id for e in entries]
        assert ids == ["M_BETA", "M_ALPHA"]

    def test_frozen_marked(self):
        """FROZEN milestone has human_review_required=True."""
        items = [
            _item("T1", "M1", risk="FROZEN"),
            _item("T2", "M1", risk="LOW"),
        ]
        bl = _backlog(items)
        entries = build_prd_500_milestone_map(bl)
        assert len(entries) == 1
        assert entries[0].human_review_required is True
        assert entries[0].risk_level == "FROZEN"

    def test_high_also_marks_review(self):
        """HIGH risk also triggers human_review_required."""
        items = [_item("T1", "M1", risk="HIGH")]
        bl = _backlog(items)
        entries = build_prd_500_milestone_map(bl)
        assert entries[0].human_review_required is True

    def test_low_no_review(self):
        """LOW/MEDIUM milestones do not require human review."""
        items = [
            _item("T1", "M1", risk="LOW"),
            _item("T2", "M1", risk="MEDIUM"),
        ]
        bl = _backlog(items)
        entries = build_prd_500_milestone_map(bl)
        assert entries[0].human_review_required is False

    def test_deterministic(self):
        """Same input always produces same output."""
        items = [
            _item("T3", "M2", risk="HIGH", status="IN_PROGRESS"),
            _item("T1", "M1", risk="LOW", status="COMPLETED"),
            _item("T2", "M1", risk="MEDIUM", status="COMPLETED"),
            _item("T4", "M2", risk="FROZEN", status="BLOCKED"),
        ]
        bl = _backlog(items)
        r1 = [milestone_map_to_dict(e) for e in build_prd_500_milestone_map(bl)]
        r2 = [milestone_map_to_dict(e) for e in build_prd_500_milestone_map(bl)]
        assert r1 == r2

    def test_start_end_task_id(self):
        items = [
            _item("T005", "MX"),
            _item("T010", "MX"),
            _item("T015", "MX"),
        ]
        bl = _backlog(items)
        entries = build_prd_500_milestone_map(bl)
        assert entries[0].start_task_id == "T005"
        assert entries[0].end_task_id == "T015"

    def test_to_dict_roundtrip(self):
        items = [_item("T1", "M1", risk="MEDIUM", status="IN_PROGRESS")]
        bl = _backlog(items)
        entries = build_prd_500_milestone_map(bl)
        d = milestone_map_to_dict(entries[0])
        assert d["milestone_id"] == "M1"
        assert d["task_count"] == 1
        assert d["risk_level"] == "MEDIUM"
        assert d["human_review_required"] is False

    def test_to_markdown_non_empty(self):
        items = [_item("T1", "M1")]
        bl = _backlog(items)
        entries = build_prd_500_milestone_map(bl)
        md = milestone_map_to_markdown(entries[0])
        assert "M1" in md
        assert "T1" in md

    def test_summarize(self):
        items = [
            _item("T1", "M1", risk="LOW"),
            _item("T2", "M1", risk="LOW"),
            _item("T3", "M2", risk="FROZEN"),
        ]
        bl = _backlog(items)
        entries = build_prd_500_milestone_map(bl)
        s = summarize_milestone_map(entries)
        assert s["milestone_count"] == 2
        assert s["total_tasks"] == 3
        assert s["human_review_required_count"] == 1

    def test_derived_status_blocked(self):
        """If any item BLOCKED, milestone status BLOCKED."""
        items = [
            _item("T1", "M1", status="COMPLETED"),
            _item("T2", "M1", status="BLOCKED"),
        ]
        bl = _backlog(items)
        entries = build_prd_500_milestone_map(bl)
        assert entries[0].status == "BLOCKED"

    def test_derived_status_completed(self):
        items = [
            _item("T1", "M1", status="COMPLETED"),
            _item("T2", "M1", status="COMPLETED"),
        ]
        bl = _backlog(items)
        entries = build_prd_500_milestone_map(bl)
        assert entries[0].status == "COMPLETED"

    def test_merged_notes_dedup(self):
        n1 = "fix auth"
        n2 = "add tests"
        items = [
            PrdBacklogItem(
                task_id="T1", title="a", milestone_id="M1", wave_id="W1",
                batch_id="B1", risk_level="LOW", status="NOT_STARTED",
                dependencies=[], allowed_file_patterns=[],
                forbidden_file_patterns=[], acceptance_command_ids=[],
                notes=[n1, n2],
            ),
            PrdBacklogItem(
                task_id="T2", title="b", milestone_id="M1", wave_id="W1",
                batch_id="B1", risk_level="LOW", status="NOT_STARTED",
                dependencies=[], allowed_file_patterns=[],
                forbidden_file_patterns=[], acceptance_command_ids=[],
                notes=[n1],
            ),
        ]
        bl = _backlog(items)
        entries = build_prd_500_milestone_map(bl)
        assert entries[0].notes == [n1, n2]
