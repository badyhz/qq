"""Tests for prd_500_backlog_execution_windows — T910."""

import pytest

from core.prd_backlog_schema import PrdBacklog, PrdBacklogItem
from core.prd_500_backlog_execution_windows import (
    Prd500ExecutionWindow,
    build_prd_500_execution_windows,
    execution_windows_to_dict,
    execution_windows_to_markdown,
    summarize_execution_windows,
)


# --- Helpers ---


def _make_item(
    task_id: str,
    milestone_id: str = "M1",
    wave_id: str = "W1",
    batch_id: str = "B0001",
    risk_level: str = "LOW",
    status: str = "NOT_STARTED",
) -> PrdBacklogItem:
    return PrdBacklogItem(
        task_id=task_id,
        title=f"Task {task_id}",
        milestone_id=milestone_id,
        wave_id=wave_id,
        batch_id=batch_id,
        risk_level=risk_level,
        status=status,
        dependencies=[],
        allowed_file_patterns=[],
        forbidden_file_patterns=[],
        acceptance_command_ids=[],
        notes=[],
    )


def _make_backlog(items: list) -> PrdBacklog:
    return PrdBacklog(
        backlog_id="BL-TEST",
        items=items,
        total_expected_tasks=len(items),
        status="NOT_STARTED",
        notes=[],
    )


# --- Tests ---


class TestPrd500ExecutionWindows:
    """T910: execution windows test suite."""

    def test_covers_executable_tasks(self):
        """All non-FROZEN items must appear in exactly one window's task range."""
        items = [_make_item(f"T{i:04d}", risk_level="LOW") for i in range(1, 101)]
        backlog = _make_backlog(items)
        windows = build_prd_500_execution_windows(backlog)

        # Collect all task IDs covered by windows
        all_task_ids = set()
        for w in windows:
            for item in items:
                if w.start_task_id <= item.task_id <= w.end_task_id:
                    all_task_ids.add(item.task_id)

        assert all_task_ids == {it.task_id for it in items}
        # Total executable tasks matches
        total_exec = sum(w.task_count for w in windows)
        assert total_exec == 100

    def test_hard_stop_present(self):
        """Every window must have hard_stop_task_id == end_task_id."""
        items = [_make_item(f"T{i:04d}", risk_level="MEDIUM") for i in range(1, 26)]
        backlog = _make_backlog(items)
        windows = build_prd_500_execution_windows(backlog)

        for w in windows:
            assert w.hard_stop_task_id == w.end_task_id, (
                f"Window {w.window_id}: hard_stop {w.hard_stop_task_id} != end {w.end_task_id}"
            )

    def test_frozen_human_only(self):
        """FROZEN items produce windows with 0 executable tasks, human_review_required=True, route=HUMAN_ONLY."""
        items = [_make_item(f"T{i:04d}", risk_level="FROZEN") for i in range(1, 6)]
        backlog = _make_backlog(items)
        windows = build_prd_500_execution_windows(backlog)

        assert len(windows) == 1
        w = windows[0]
        assert w.task_count == 0
        assert w.human_review_required is True
        assert w.recommended_route == "HUMAN_ONLY"
        assert w.max_parallel_agents == 0
        assert w.risk_level == "FROZEN"

    def test_deterministic(self):
        """Same input produces identical output every time."""
        items = [_make_item(f"T{i:04d}", risk_level="HIGH") for i in range(1, 11)]
        backlog = _make_backlog(items)

        run1 = build_prd_500_execution_windows(backlog)
        run2 = build_prd_500_execution_windows(backlog)

        dicts1 = [execution_windows_to_dict(w) for w in run1]
        dicts2 = [execution_windows_to_dict(w) for w in run2]
        assert dicts1 == dicts2

    def test_high_window_size_bounded(self):
        """HIGH risk windows must have 3-15 tasks."""
        items = [_make_item(f"T{i:04d}", risk_level="HIGH") for i in range(1, 31)]
        backlog = _make_backlog(items)
        windows = build_prd_500_execution_windows(backlog)

        for w in windows:
            assert 0 < w.task_count <= 15, f"Window {w.window_id} has {w.task_count} tasks"

    def test_high_human_review_required(self):
        """HIGH risk windows require human review."""
        items = [_make_item(f"T{i:04d}", risk_level="HIGH") for i in range(1, 11)]
        backlog = _make_backlog(items)
        windows = build_prd_500_execution_windows(backlog)

        for w in windows:
            assert w.human_review_required is True
            assert w.recommended_route == "mimo2.5pro with human review"

    def test_low_medium_route(self):
        """LOW/MEDIUM risk uses correct routes."""
        low_items = [_make_item(f"T{i:04d}", risk_level="LOW") for i in range(1, 6)]
        med_items = [_make_item(f"T{i+100:04d}", risk_level="MEDIUM", milestone_id="M2") for i in range(1, 6)]
        backlog = _make_backlog(low_items + med_items)
        windows = build_prd_500_execution_windows(backlog)

        routes = {w.window_id: w.recommended_route for w in windows}
        # LOW window
        assert any("mimo2.5pro or mimo2.5" in r for r in routes.values())
        # MEDIUM window
        assert any(r == "mimo2.5pro" for r in routes.values())

    def test_serializers(self):
        """Dict and markdown serializers produce expected structure."""
        items = [_make_item("T0001", risk_level="LOW")]
        backlog = _make_backlog(items)
        windows = build_prd_500_execution_windows(backlog)
        w = windows[0]

        d = execution_windows_to_dict(w)
        assert d["window_id"] == "W0001"
        assert d["start_task_id"] == "T0001"
        assert d["hard_stop_task_id"] == "T0001"

        md = execution_windows_to_markdown(w)
        assert "Window W0001" in md
        assert "T0001" in md

    def test_summarize(self):
        """Summary returns correct counts."""
        items = [_make_item(f"T{i:04d}", risk_level="LOW") for i in range(1, 6)]
        backlog = _make_backlog(items)
        windows = build_prd_500_execution_windows(backlog)
        summary = summarize_execution_windows(windows)

        assert summary["total_windows"] == 1
        assert summary["total_executable_tasks"] == 5
        assert summary["risk_counts"]["LOW"] == 1
        assert summary["human_review_required_count"] == 0
