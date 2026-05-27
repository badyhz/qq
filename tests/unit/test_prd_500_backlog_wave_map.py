"""Tests for PRD 500 backlog wave map — T906."""

from core.prd_backlog_schema import PrdBacklog, PrdBacklogItem
from core.prd_500_backlog_wave_map import (
    Prd500WaveMapEntry,
    build_prd_500_wave_map,
    wave_map_to_dict,
    wave_map_to_markdown,
    summarize_wave_map,
)


def _make_item(task_id: str, milestone_id: str, risk: str = "LOW") -> PrdBacklogItem:
    return PrdBacklogItem(
        task_id=task_id,
        title=f"Task {task_id}",
        milestone_id=milestone_id,
        wave_id="",
        batch_id="",
        risk_level=risk,
        status="PENDING",
        dependencies=[],
        allowed_file_patterns=[],
        forbidden_file_patterns=[],
        acceptance_command_ids=[],
        notes=[],
    )


def _make_backlog(items):
    return PrdBacklog(
        backlog_id="TEST-500",
        items=items,
        total_expected_tasks=len(items),
        status="OPEN",
        notes=[],
    )


class TestWaveMap:
    def test_covers_all_items(self):
        """Every backlog item must appear in exactly one wave."""
        items = []
        for i in range(60):
            ms = f"MS{i // 20 + 1}"
            items.append(_make_item(f"T{i:03d}", ms))
        backlog = _make_backlog(items)
        entries = build_prd_500_wave_map(backlog, max_tasks_per_wave=25)

        # Collect all task ranges
        covered = set()
        for e in entries:
            # We know items are ordered; verify count matches range
            covered.add(e.milestone_id)

        # Total task_count across all waves must equal backlog size
        total = sum(e.task_count for e in entries)
        assert total == 60, f"Expected 60 tasks covered, got {total}"
        # All milestones present
        assert covered == {"MS1", "MS2", "MS3"}

    def test_wave_size_leq_25(self):
        """No wave may exceed max_tasks_per_wave."""
        items = [_make_item(f"T{i:03d}", "MS1") for i in range(100)]
        backlog = _make_backlog(items)
        entries = build_prd_500_wave_map(backlog, max_tasks_per_wave=25)
        for e in entries:
            assert e.task_count <= 25, f"{e.wave_id} has {e.task_count} tasks"

    def test_frozen_blocked(self):
        """FROZEN waves must have 0 parallel agents and HUMAN_ONLY route."""
        items = [_make_item(f"T{i:03d}", "MS1", risk="FROZEN") for i in range(5)]
        backlog = _make_backlog(items)
        entries = build_prd_500_wave_map(backlog)
        for e in entries:
            assert e.max_parallel_agents == 0
            assert e.recommended_route == "HUMAN_ONLY"

    def test_deterministic(self):
        """Same input produces same output every time."""
        items = [_make_item(f"T{i:03d}", f"MS{i % 3 + 1}") for i in range(30)]
        backlog = _make_backlog(items)
        r1 = build_prd_500_wave_map(backlog)
        r2 = build_prd_500_wave_map(backlog)
        assert r1 == r2

    def test_high_risk_parallelism(self):
        """HIGH risk waves max 3 parallel agents."""
        items = [_make_item(f"T{i:03d}", "MS1", risk="HIGH") for i in range(10)]
        backlog = _make_backlog(items)
        entries = build_prd_500_wave_map(backlog)
        for e in entries:
            assert e.max_parallel_agents <= 3
            assert e.recommended_route == "mimo2.5pro with human review"

    def test_low_medium_parallelism(self):
        """LOW/MEDIUM risk waves max 8 parallel agents."""
        for risk in ("LOW", "MEDIUM"):
            items = [_make_item(f"T{i:03d}", "MS1", risk=risk) for i in range(5)]
            backlog = _make_backlog(items)
            entries = build_prd_500_wave_map(backlog)
            for e in entries:
                assert e.max_parallel_agents <= 8

    def test_dominant_risk_in_mixed_milestone(self):
        """If a milestone has any FROZEN item, entire milestone wave is FROZEN."""
        items = [
            _make_item("T000", "MS1", risk="LOW"),
            _make_item("T001", "MS1", risk="FROZEN"),
        ]
        backlog = _make_backlog(items)
        entries = build_prd_500_wave_map(backlog)
        assert entries[0].risk_level == "FROZEN"
        assert entries[0].max_parallel_agents == 0

    def test_serializers(self):
        """wave_map_to_dict and wave_map_to_markdown produce expected shapes."""
        items = [_make_item("T000", "MS1", risk="LOW")]
        backlog = _make_backlog(items)
        entries = build_prd_500_wave_map(backlog)
        d = wave_map_to_dict(entries[0])
        assert isinstance(d, dict)
        assert d["wave_id"] == entries[0].wave_id
        md = wave_map_to_markdown(entries[0])
        assert entries[0].wave_id in md

    def test_summarize(self):
        """summarize_wave_map returns correct aggregate counts."""
        items = [_make_item(f"T{i:03d}", f"MS{i % 2 + 1}") for i in range(50)]
        backlog = _make_backlog(items)
        entries = build_prd_500_wave_map(backlog, max_tasks_per_wave=25)
        summary = summarize_wave_map(entries)
        assert summary["total_tasks"] == 50
        assert summary["milestone_count"] == 2
        assert summary["wave_count"] == len(entries)
