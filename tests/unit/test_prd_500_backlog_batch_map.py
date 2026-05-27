"""Tests for prd_500_backlog_batch_map — T907."""

from core.prd_backlog_schema import PrdBacklog, PrdBacklogItem
from core.prd_500_backlog_batch_map import (
    Prd500BatchMapEntry,
    batch_map_to_dict,
    batch_map_to_markdown,
    build_prd_500_batch_map,
    summarize_batch_map,
)

# --- Helpers ---


def _make_item(task_id: str, milestone_id: str, wave_id: str, risk_level: str = "LOW"):
    return PrdBacklogItem(
        task_id=task_id,
        title=f"Task {task_id}",
        milestone_id=milestone_id,
        wave_id=wave_id,
        batch_id="",
        risk_level=risk_level,
        status="NOT_STARTED",
        dependencies=[],
        allowed_file_patterns=[],
        forbidden_file_patterns=[],
        acceptance_command_ids=[],
        notes=[],
    )


def _make_backlog(items):
    return PrdBacklog(
        backlog_id="TEST-BL",
        items=items,
        total_expected_tasks=len(items),
        status="OPEN",
        notes=[],
    )


# --- Tests ---


class TestBatchMap:
    def test_covers_all_items(self):
        items = [
            _make_item(f"T{i:04d}", f"M{(i // 5) + 1}", f"W{(i // 5) + 1}")
            for i in range(25)
        ]
        backlog = _make_backlog(items)
        entries = build_prd_500_batch_map(backlog)
        total = sum(e.task_count for e in entries)
        assert total == 25

    def test_batch_size_leq_10(self):
        items = [
            _make_item(f"T{i:04d}", "M1", "W1") for i in range(35)
        ]
        backlog = _make_backlog(items)
        entries = build_prd_500_batch_map(backlog)
        for e in entries:
            assert e.task_count <= 10

    def test_hard_stop_set(self):
        items = [
            _make_item(f"T{i:04d}", "M1", "W1") for i in range(15)
        ]
        backlog = _make_backlog(items)
        entries = build_prd_500_batch_map(backlog)
        for e in entries:
            assert e.hard_stop_task_id == e.end_task_id
            assert e.hard_stop_task_id != ""

    def test_deterministic(self):
        items = [
            _make_item(f"T{i:04d}", f"M{(i // 3) + 1}", f"W{(i // 3) + 1}")
            for i in range(20)
        ]
        backlog = _make_backlog(items)
        run1 = build_prd_500_batch_map(backlog)
        run2 = build_prd_500_batch_map(backlog)
        assert [batch_map_to_dict(e) for e in run1] == [
            batch_map_to_dict(e) for e in run2
        ]

    def test_risk_agent_count_rules(self):
        items = [
            _make_item("T0000", "M1", "W1", "LOW"),
            _make_item("T0001", "M1", "W1", "MEDIUM"),
            _make_item("T0002", "M1", "W1", "HIGH"),
            _make_item("T0003", "M1", "W1", "FROZEN"),
        ]
        backlog = _make_backlog(items)
        entries = build_prd_500_batch_map(backlog)
        assert len(entries) == 1
        e = entries[0]
        # HIGH dominates when mixed with LOW/MEDIUM/FROZEN
        assert e.risk_level == "HIGH"
        assert e.recommended_agent_count == 3

    def test_frozen_only_batch(self):
        items = [
            _make_item(f"T{i:04d}", "M1", "W1", "FROZEN") for i in range(5)
        ]
        backlog = _make_backlog(items)
        entries = build_prd_500_batch_map(backlog)
        assert entries[0].risk_level == "FROZEN"
        assert entries[0].recommended_agent_count == 0

    def test_serializers(self):
        items = [
            _make_item("T0000", "M1", "W1"),
            _make_item("T0001", "M1", "W1"),
        ]
        backlog = _make_backlog(items)
        entries = build_prd_500_batch_map(backlog)
        d = batch_map_to_dict(entries[0])
        assert d["batch_id"] == entries[0].batch_id
        md = batch_map_to_markdown(entries[0])
        assert "Batch" in md

    def test_summary(self):
        items = [
            _make_item(f"T{i:04d}", "M1", "W1") for i in range(22)
        ]
        backlog = _make_backlog(items)
        entries = build_prd_500_batch_map(backlog)
        s = summarize_batch_map(entries)
        assert s["total_batches"] == 3  # 10 + 10 + 2
        assert s["total_tasks"] == 22
