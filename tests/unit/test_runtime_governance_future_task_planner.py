"""Tests for runtime governance future task planner."""

import pytest

from core.runtime_governance_future_task_planner import (
    RuntimeGovernanceFutureTask,
    build_runtime_governance_future_task_plan,
    future_task_plan_to_dict,
    future_task_plan_to_markdown,
)


class TestBuildPlan:
    def test_returns_6_tasks(self):
        plan = build_runtime_governance_future_task_plan()
        assert len(plan) == 6

    def test_all_tasks_are_frozen_dataclass(self):
        plan = build_runtime_governance_future_task_plan()
        for t in plan:
            assert isinstance(t, RuntimeGovernanceFutureTask)
            with pytest.raises(AttributeError):
                t.task_id = "mutated"

    def test_task_ids_unique(self):
        plan = build_runtime_governance_future_task_plan()
        ids = [t.task_id for t in plan]
        assert len(ids) == len(set(ids))

    def test_expected_task_ids_present(self):
        plan = build_runtime_governance_future_task_plan()
        ids = {t.task_id for t in plan}
        expected = {
            "runtime_readonly_hook",
            "no_submit_assertion",
            "dry_run_evidence_writer",
            "manual_approval_cli",
            "planner_integration_review",
            "live_submit_frozen",
        }
        assert ids == expected

    def test_risk_levels_valid(self):
        plan = build_runtime_governance_future_task_plan()
        valid = {"low", "medium", "high", "critical"}
        for t in plan:
            assert t.risk_level in valid, f"{t.task_id} has invalid risk_level: {t.risk_level}"

    def test_high_risk_tasks_have_hold_notes(self):
        plan = build_runtime_governance_future_task_plan()
        for t in plan:
            if t.risk_level in ("high", "critical"):
                assert "HOLD" in t.notes, f"{t.task_id} (risk={t.risk_level}) missing HOLD note"

    def test_live_submit_frozen_is_critical(self):
        plan = build_runtime_governance_future_task_plan()
        t = next(x for x in plan if x.task_id == "live_submit_frozen")
        assert t.risk_level == "critical"
        assert "HOLD" in t.notes


class TestToDict:
    def test_roundtrip_length(self):
        plan = build_runtime_governance_future_task_plan()
        dicts = future_task_plan_to_dict(plan)
        assert len(dicts) == 6

    def test_all_keys_present(self):
        plan = build_runtime_governance_future_task_plan()
        dicts = future_task_plan_to_dict(plan)
        for d in dicts:
            assert set(d.keys()) == {
                "task_id",
                "title",
                "risk_level",
                "dependencies",
                "allowed_files_hint",
                "notes",
            }

    def test_values_match_source(self):
        plan = build_runtime_governance_future_task_plan()
        dicts = future_task_plan_to_dict(plan)
        for t, d in zip(plan, dicts):
            assert d["task_id"] == t.task_id
            assert d["title"] == t.title
            assert d["risk_level"] == t.risk_level


class TestToMarkdown:
    def test_contains_header(self):
        plan = build_runtime_governance_future_task_plan()
        md = future_task_plan_to_markdown(plan)
        assert "# Runtime Governance Future Task Plan" in md

    def test_contains_all_task_ids(self):
        plan = build_runtime_governance_future_task_plan()
        md = future_task_plan_to_markdown(plan)
        for t in plan:
            assert t.task_id in md

    def test_contains_table_separator(self):
        plan = build_runtime_governance_future_task_plan()
        md = future_task_plan_to_markdown(plan)
        assert "|---" in md

    def test_line_count(self):
        plan = build_runtime_governance_future_task_plan()
        md = future_task_plan_to_markdown(plan)
        lines = md.strip().split("\n")
        # header(1) + blank(1) + table_header(1) + separator(1) + 6 rows = 10
        assert len(lines) == 10
