"""Tests for PRD agent execution window recommender — T879.

Deterministic, no I/O, no timestamps, no random.
"""

import pytest

from core.prd_backlog_schema import PrdBacklogItem
from core.prd_agent_execution_window_recommender import (
    PrdExecutionWindowRecommendation,
    recommend_execution_window,
    recommend_window_for_tasks,
    execution_window_to_dict,
    execution_window_to_markdown,
)


# --- Helpers ---


def _make_item(task_id: str, risk: str, deps: list = None) -> PrdBacklogItem:
    return PrdBacklogItem(
        task_id=task_id,
        title=f"Task {task_id}",
        milestone_id="M1",
        wave_id="W1",
        batch_id="B1",
        risk_level=risk,
        status="PENDING",
        dependencies=deps or [],
        allowed_file_patterns=["*"],
        forbidden_file_patterns=[],
        acceptance_command_ids=[],
        notes=[],
    )


# --- recommend_execution_window ---


class TestRecommendExecutionWindow:
    def test_low_low(self):
        rec = recommend_execution_window("LOW", "low")
        assert rec.recommended_task_count_min == 20
        assert rec.recommended_task_count_max == 50
        assert rec.recommended_agent_count_max == 8
        assert rec.recommended_route == "mimo2.5pro or mimo2.5"
        assert rec.hard_stop_required is False

    def test_low_medium(self):
        rec = recommend_execution_window("LOW", "medium")
        assert rec.recommended_task_count_min == 15
        assert rec.recommended_task_count_max == 40
        assert rec.recommended_agent_count_max == 7
        assert rec.recommended_route == "mimo2.5pro or mimo2.5"

    def test_low_high(self):
        rec = recommend_execution_window("LOW", "high")
        assert rec.recommended_task_count_min == 10
        assert rec.recommended_task_count_max == 30
        assert rec.recommended_agent_count_max == 6

    def test_medium(self):
        rec = recommend_execution_window("MEDIUM", "low")
        assert rec.recommended_task_count_min == 10
        assert rec.recommended_task_count_max == 30
        assert rec.recommended_agent_count_max == 6
        assert rec.recommended_route == "mimo2.5pro"

    def test_high_caps_at_10(self):
        rec = recommend_execution_window("HIGH", "low")
        assert rec.recommended_task_count_min == 3
        assert rec.recommended_task_count_max == 10
        assert rec.recommended_agent_count_max == 3
        assert rec.hard_stop_required is True
        assert "human review" in rec.recommended_route

    def test_high_high_density(self):
        rec = recommend_execution_window("HIGH", "high")
        assert rec.recommended_task_count_max == 5
        assert rec.recommended_agent_count_max == 2

    def test_frozen_blocks(self):
        rec = recommend_execution_window("FROZEN", "low")
        assert rec.recommended_task_count_min == 0
        assert rec.recommended_task_count_max == 0
        assert rec.recommended_agent_count_max == 0
        assert rec.recommended_route == "HUMAN_ONLY"
        assert rec.hard_stop_required is True

    def test_frozen_all_densities(self):
        for d in ("low", "medium", "high"):
            rec = recommend_execution_window("FROZEN", d)
            assert rec.recommended_task_count_min == 0
            assert rec.recommended_task_count_max == 0
            assert rec.recommended_agent_count_max == 0
            assert rec.recommended_route == "HUMAN_ONLY"

    def test_invalid_risk(self):
        with pytest.raises(ValueError, match="Invalid risk_level"):
            recommend_execution_window("BANANA", "low")

    def test_invalid_density(self):
        with pytest.raises(ValueError, match="Invalid dependency_density"):
            recommend_execution_window("LOW", "extreme")


# --- recommend_window_for_tasks ---


class TestRecommendWindowForTasks:
    def test_empty_tasks(self):
        rec = recommend_window_for_tasks([])
        assert rec.risk_level == "LOW"
        assert rec.recommended_task_count_min == 20

    def test_mixed_tasks_uses_highest_risk(self):
        items = [
            _make_item("T1", "LOW"),
            _make_item("T2", "MEDIUM"),
            _make_item("T3", "HIGH"),
            _make_item("T4", "LOW"),
        ]
        rec = recommend_window_for_tasks(items)
        assert rec.risk_level == "HIGH"
        assert rec.hard_stop_required is True

    def test_frozen_wins_over_all(self):
        items = [
            _make_item("T1", "LOW"),
            _make_item("T2", "MEDIUM"),
            _make_item("T3", "FROZEN"),
        ]
        rec = recommend_window_for_tasks(items)
        assert rec.risk_level == "FROZEN"
        assert rec.recommended_task_count_max == 0

    def test_high_dependency_density(self):
        # 3/4 items have deps -> ratio=0.75 -> high
        items = [
            _make_item("T1", "LOW", ["T2"]),
            _make_item("T2", "LOW", ["T3"]),
            _make_item("T3", "LOW", ["T1"]),
            _make_item("T4", "LOW"),
        ]
        rec = recommend_window_for_tasks(items)
        assert rec.dependency_density == "high"

    def test_medium_dependency_density(self):
        # 1/5 items have deps -> ratio=0.2 -> medium
        items = [
            _make_item("T1", "LOW", ["T2"]),
            _make_item("T2", "LOW"),
            _make_item("T3", "LOW"),
            _make_item("T4", "LOW"),
            _make_item("T5", "LOW"),
        ]
        rec = recommend_window_for_tasks(items)
        assert rec.dependency_density == "medium"

    def test_low_dependency_density(self):
        # 0 deps
        items = [_make_item(f"T{i}", "LOW") for i in range(10)]
        rec = recommend_window_for_tasks(items)
        assert rec.dependency_density == "low"


# --- Determinism ---


class TestDeterminism:
    def test_same_input_same_output(self):
        a = recommend_execution_window("HIGH", "medium")
        b = recommend_execution_window("HIGH", "medium")
        assert execution_window_to_dict(a) == execution_window_to_dict(b)

    def test_frozen_dataclass(self):
        rec = recommend_execution_window("LOW", "low")
        with pytest.raises(AttributeError):
            rec.risk_level = "CHANGED"


# --- Serializers ---


class TestSerializers:
    def test_to_dict_keys(self):
        rec = recommend_execution_window("MEDIUM", "low")
        d = execution_window_to_dict(rec)
        expected_keys = {
            "risk_level", "dependency_density",
            "recommended_task_count_min", "recommended_task_count_max",
            "recommended_agent_count_max", "recommended_route",
            "hard_stop_required", "notes",
        }
        assert set(d.keys()) == expected_keys

    def test_to_markdown_contains_table(self):
        rec = recommend_execution_window("HIGH", "low")
        md = execution_window_to_markdown(rec)
        assert "## Execution Window Recommendation" in md
        assert "| Risk Level | HIGH |" in md
        assert "3-10" in md
        assert "yes" in md

    def test_to_markdown_frozen(self):
        rec = recommend_execution_window("FROZEN", "medium")
        md = execution_window_to_markdown(rec)
        assert "HUMAN_ONLY" in md
        assert "no automated" in md.lower() or "FROZEN" in md

    def test_to_markdown_notes(self):
        rec = recommend_execution_window("HIGH", "high")
        md = execution_window_to_markdown(rec)
        assert "**Notes:**" in md
        assert "human review" in md.lower()
        assert "ordering constraints" in md.lower()

    def test_to_dict_notes_is_copy(self):
        rec = recommend_execution_window("LOW", "low")
        d = execution_window_to_dict(rec)
        # Modifying dict notes shouldn't affect original
        d["notes"].append("extra")
        assert len(rec.notes) == 0
