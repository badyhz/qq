"""Tests for PRD milestone planner — T874."""

from core.prd_backlog_schema import PrdBacklogItem
from core.prd_milestone_planner import (
    PrdMilestone,
    milestones_to_dict,
    milestones_to_markdown,
    milestone_to_dict,
    milestone_to_markdown,
    plan_milestones_from_backlog,
    summarize_milestones,
)


def _make_item(task_num: int, risk: str = "LOW") -> PrdBacklogItem:
    return PrdBacklogItem(
        task_id=f"T{task_num}",
        title=f"Task {task_num}",
        milestone_id="",
        wave_id="",
        batch_id="",
        risk_level=risk,
        status="NOT_STARTED",
        dependencies=[],
        allowed_file_patterns=[],
        forbidden_file_patterns=[],
        acceptance_command_ids=[],
        notes=[],
    )


class TestPlanMilestonesFromBacklog:
    def test_120_tasks_split_into_3_milestones(self):
        items = [_make_item(i) for i in range(1, 121)]
        result = plan_milestones_from_backlog(items, max_tasks_per_milestone=50)
        assert len(result) == 3
        assert len(result[0].task_ids) == 50
        assert len(result[1].task_ids) == 50
        assert len(result[2].task_ids) == 20

    def test_frozen_item_makes_milestone_frozen(self):
        items = [_make_item(i) for i in range(1, 6)]
        items[2] = _make_item(3, risk="FROZEN")
        result = plan_milestones_from_backlog(items, max_tasks_per_milestone=50)
        assert len(result) == 1
        assert result[0].risk_level == "FROZEN"
        assert result[0].recommended_execution_mode == "HUMAN_REVIEW_REQUIRED"

    def test_ordering_preserved(self):
        # Pass items out of order; planner should sort by task number.
        items = [_make_item(10), _make_item(1), _make_item(5)]
        result = plan_milestones_from_backlog(items, max_tasks_per_milestone=50)
        assert result[0].task_ids == ["T1", "T5", "T10"]

    def test_deterministic_markdown(self):
        items = [_make_item(i) for i in range(1, 4)]
        result = plan_milestones_from_backlog(items)
        md1 = milestones_to_markdown(result)
        md2 = milestones_to_markdown(result)
        assert md1 == md2

    def test_summary_counts_milestones(self):
        items = [_make_item(i) for i in range(1, 121)]
        result = plan_milestones_from_backlog(items, max_tasks_per_milestone=50)
        summary = summarize_milestones(result)
        assert summary["total_milestones"] == 3
        assert summary["total_tasks"] == 120

    def test_high_risk_propagation(self):
        items = [_make_item(i, risk="HIGH") for i in range(1, 6)]
        result = plan_milestones_from_backlog(items)
        assert result[0].risk_level == "HIGH"
        # 5 tasks <= 15 so SMALL_BATCH even at HIGH risk
        assert result[0].recommended_execution_mode == "SMALL_BATCH"

    def test_small_batch_mode(self):
        items = [_make_item(i) for i in range(1, 11)]
        result = plan_milestones_from_backlog(items)
        assert result[0].recommended_execution_mode == "SMALL_BATCH"

    def test_pro_multi_wave_mode(self):
        items = [_make_item(i) for i in range(1, 21)]
        result = plan_milestones_from_backlog(items)
        assert result[0].recommended_execution_mode == "PRO_MULTI_WAVE"

    def test_empty_items(self):
        result = plan_milestones_from_backlog([])
        assert result == []

    def test_dependencies_collected(self):
        item_a = PrdBacklogItem(
            task_id="T1", title="A", milestone_id="", wave_id="",
            batch_id="", risk_level="LOW", status="NOT_STARTED",
            dependencies=["T0"], allowed_file_patterns=[],
            forbidden_file_patterns=[], acceptance_command_ids=[], notes=[],
        )
        item_b = PrdBacklogItem(
            task_id="T2", title="B", milestone_id="", wave_id="",
            batch_id="", risk_level="LOW", status="NOT_STARTED",
            dependencies=["T1"], allowed_file_patterns=[],
            forbidden_file_patterns=[], acceptance_command_ids=[], notes=[],
        )
        result = plan_milestones_from_backlog([item_a, item_b])
        # T0 is external, T1 is internal to milestone
        assert "T0" in result[0].dependencies
        assert "T1" not in result[0].dependencies

    def test_milestone_to_dict_roundtrip(self):
        items = [_make_item(i) for i in range(1, 4)]
        result = plan_milestones_from_backlog(items)
        d = milestone_to_dict(result[0])
        assert d["milestone_id"] == result[0].milestone_id
        assert d["task_ids"] == ["T1", "T2", "T3"]
        assert d["risk_level"] == "LOW"

    def test_milestones_to_dict_list(self):
        items = [_make_item(i) for i in range(1, 4)]
        result = plan_milestones_from_backlog(items)
        dl = milestones_to_dict(result)
        assert isinstance(dl, list)
        assert len(dl) == 1

    def test_milestone_markdown_contains_task_ids(self):
        items = [_make_item(i) for i in range(1, 4)]
        result = plan_milestones_from_backlog(items)
        md = milestone_to_markdown(result[0])
        assert "- T1" in md
        assert "- T2" in md
        assert "- T3" in md
