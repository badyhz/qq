"""Tests for T845: Runtime governance read-only rollback plan."""

import pytest

from core.runtime_governance_readonly_rollback_plan import (
    RuntimeGovernanceReadOnlyRollbackStep,
    build_readonly_rollback_plan,
    readonly_rollback_plan_to_dict,
    readonly_rollback_plan_to_markdown,
)


class TestBuildReadonlyRollbackPlan:
    """Test build_readonly_rollback_plan."""

    def test_returns_exactly_5_steps(self):
        steps = build_readonly_rollback_plan()
        assert len(steps) == 5

    def test_all_triggers_present(self):
        steps = build_readonly_rollback_plan()
        triggers = {s.trigger for s in steps}
        expected = {
            "unexpected write permission",
            "network call detected",
            "secret access detected",
            "planner bypass detected",
            "permission creep detected",
        }
        assert triggers == expected

    def test_all_actions_contain_halt_or_revert(self):
        steps = build_readonly_rollback_plan()
        for s in steps:
            assert (
                "halt" in s.action or "revert" in s.action
            ), f"step {s.step_id} action missing halt/revert: {s.action}"

    def test_deterministic(self):
        a = build_readonly_rollback_plan()
        b = build_readonly_rollback_plan()
        assert a == b

    def test_step_ids_unique(self):
        steps = build_readonly_rollback_plan()
        ids = [s.step_id for s in steps]
        assert len(ids) == len(set(ids))

    def test_all_fields_populated(self):
        steps = build_readonly_rollback_plan()
        for s in steps:
            assert s.step_id
            assert s.trigger
            assert s.action
            assert s.verification
            assert s.owner


class TestReadonlyRollbackPlanToDict:
    """Test readonly_rollback_plan_to_dict."""

    def test_returns_list_of_dicts(self):
        steps = build_readonly_rollback_plan()
        result = readonly_rollback_plan_to_dict(steps)
        assert isinstance(result, list)
        assert len(result) == 5
        for d in result:
            assert isinstance(d, dict)
            assert set(d.keys()) == {
                "step_id",
                "trigger",
                "action",
                "verification",
                "owner",
            }


class TestReadonlyRollbackPlanToMarkdown:
    """Test readonly_rollback_plan_to_markdown."""

    def test_contains_all_step_ids(self):
        steps = build_readonly_rollback_plan()
        md = readonly_rollback_plan_to_markdown(steps)
        for s in steps:
            assert s.step_id in md

    def test_contains_table_header(self):
        steps = build_readonly_rollback_plan()
        md = readonly_rollback_plan_to_markdown(steps)
        assert "step_id" in md
        assert "trigger" in md
        assert "action" in md
        assert "verification" in md
        assert "owner" in md
