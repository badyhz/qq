"""Unit tests for quant_workflow_policy — pure validation, no mocks."""
from __future__ import annotations

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.quant_workflow_policy import (
    BLOCKED_ACTIONS,
    ALLOWED_CATEGORIES,
    QuantPolicyViolation,
    QuantWorkflowPolicy,
    validate_quant_safety,
)


class TestQuantPolicyViolation:
    def test_dataclass_fields(self):
        v = QuantPolicyViolation(rule="R", severity="CRITICAL", detail="d", task_id="t1")
        assert v.rule == "R"
        assert v.severity == "CRITICAL"
        assert v.detail == "d"
        assert v.task_id == "t1"

    def test_optional_task_id(self):
        v = QuantPolicyViolation(rule="R", severity="HIGH", detail="d")
        assert v.task_id is None


class TestConstants:
    def test_blocked_actions_contents(self):
        expected = {"submit", "cancel", "flatten", "live_execution", "planner_escalation", "place_order", "close_position"}
        assert BLOCKED_ACTIONS == expected

    def test_allowed_categories_contents(self):
        expected = {"READONLY", "AUDIT", "DOCS", "SIMULATION", "CLOSEOUT"}
        assert ALLOWED_CATEGORIES == expected


class TestQuantWorkflowPolicy:
    def test_is_allowed(self):
        p = QuantWorkflowPolicy()
        for cat in ALLOWED_CATEGORIES:
            assert p.is_allowed(cat) is True

    def test_is_not_allowed_blocked_action(self):
        p = QuantWorkflowPolicy()
        for action in BLOCKED_ACTIONS:
            assert p.is_allowed(action) is False

    def test_is_not_allowed_unknown_category(self):
        p = QuantWorkflowPolicy()
        assert p.is_allowed("UNKNOWN") is False
        assert p.is_allowed("LIVE_TRADING") is False

    def test_validate_task_allowed(self):
        p = QuantWorkflowPolicy()
        violations = p.validate_task("t1", "READONLY")
        assert violations == []

    def test_validate_task_blocked_category(self):
        p = QuantWorkflowPolicy()
        vs = p.validate_task("t1", "LIVE_TRADING")
        assert len(vs) == 1
        assert vs[0].rule == "BLOCKED_CATEGORY"
        assert vs[0].severity == "CRITICAL"
        assert vs[0].task_id == "t1"

    def test_validate_task_blocked_action(self):
        p = QuantWorkflowPolicy()
        vs = p.validate_task("t1", "submit")
        assert len(vs) == 2
        rules = {v.rule for v in vs}
        assert "BLOCKED_ACTION" in rules
        assert "BLOCKED_CATEGORY" in rules

    def test_validate_task_all_blocked_actions_detected(self):
        p = QuantWorkflowPolicy()
        for action in BLOCKED_ACTIONS:
            vs = p.validate_task("t1", action)
            rules = {v.rule for v in vs}
            assert "BLOCKED_ACTION" in rules, f"BLOCKED_ACTION missing for '{action}'"

    def test_validate_workflow_policy_empty(self):
        p = QuantWorkflowPolicy()
        assert p.validate_workflow_policy([]) == []

    def test_validate_workflow_policy_mixed(self):
        p = QuantWorkflowPolicy()
        tasks = [
            {"id": "t1", "category": "READONLY"},
            {"id": "t2", "category": "submit"},
            {"id": "t3", "category": "AUDIT"},
            {"id": "t4", "category": "flatten"},
            {"id": "t5", "category": "UNKNOWN"},
        ]
        vs = p.validate_workflow_policy(tasks)
        assert len(vs) == 5
        task_ids = [v.task_id for v in vs]
        assert "t2" in task_ids
        assert "t4" in task_ids
        assert "t5" in task_ids
        # Allowed tasks produce no violations
        clean_ids = {v.task_id for v in vs}
        assert "t1" not in clean_ids
        assert "t3" not in clean_ids

    def test_validate_workflow_policy_missing_category(self):
        p = QuantWorkflowPolicy()
        tasks = [{"id": "t1"}]
        vs = p.validate_workflow_policy(tasks)
        assert len(vs) == 1
        assert vs[0].rule == "BLOCKED_CATEGORY"


class TestValidateQuantSafety:
    def test_safe_workflow(self):
        result = validate_quant_safety({"tasks": [{"id": "t1", "category": "READONLY"}]})
        assert result["safe"] is True
        assert result["violations"] == []

    def test_unsafe_workflow(self):
        result = validate_quant_safety({"tasks": [{"id": "t1", "category": "submit"}]})
        assert result["safe"] is False
        assert len(result["violations"]) == 2
        rules = {v["rule"] for v in result["violations"]}
        assert "BLOCKED_ACTION" in rules
        assert "BLOCKED_CATEGORY" in rules

    def test_empty_tasks(self):
        result = validate_quant_safety({})
        assert result["safe"] is True

    def test_summary_present(self):
        result = validate_quant_safety({})
        assert "blocked_actions" in result["summary"]
        assert "allowed_categories" in result["summary"]


class TestSummary:
    def test_summary_keys(self):
        p = QuantWorkflowPolicy()
        s = p.summary()
        assert set(s.keys()) == {"blocked_actions", "allowed_categories", "blocked_count", "allowed_count"}

    def test_summary_counts(self):
        p = QuantWorkflowPolicy()
        s = p.summary()
        assert s["blocked_count"] == len(BLOCKED_ACTIONS)
        assert s["allowed_count"] == len(ALLOWED_CATEGORIES)


class TestIntegrationWithWorkflowSafety:
    def test_both_validators_on_same_workflow(self):
        from core.workflow_safety import WorkflowSafetyValidator, validate_workflow_safety

        workflow = {
            "mode": "READONLY",
            "tasks": [
                {"id": "t1", "category": "READONLY", "deps": []},
                {"id": "t2", "category": "AUDIT", "deps": ["t1"]},
            ],
        }

        # WorkflowSafetyValidator
        wsv = WorkflowSafetyValidator()
        wsv_violations = wsv.validate_workflow(workflow)
        assert len(wsv_violations) == 0

        # QuantWorkflowPolicy
        result = validate_quant_safety(workflow)
        assert result["safe"] is True

        # Both pass
        assert len(wsv_violations) == 0 and result["safe"] is True

    def test_both_detect_different_issues(self):
        workflow = {
            "mode": "LIVE_EXECUTION",
            "tasks": [{"id": "t1", "category": "submit"}],
        }

        from core.workflow_safety import WorkflowSafetyValidator

        wsv = WorkflowSafetyValidator()
        wsv_violations = wsv.validate_workflow(workflow)
        assert len(wsv_violations) > 0  # LIVE_EXECUTION mode blocked

        result = validate_quant_safety(workflow)
        assert result["safe"] is False  # submit blocked

        # Both catch issues, potentially different ones
        assert len(wsv_violations) > 0 and not result["safe"]

    def test_frozen_pattern_with_quant_policy(self):
        from core.workflow_safety import WorkflowSafetyValidator

        # WorkflowSafetyValidator catches frozen file access via validate_frozen_exclusion
        workflow = {
            "mode": "READONLY",
            "tasks": [{"id": "t1", "category": "READONLY"}],
        }

        wsv = WorkflowSafetyValidator()
        frozen_violations = wsv.validate_frozen_exclusion("t1", ["core/live_runner.py"])
        assert len(frozen_violations) > 0

        # QuantWorkflowPolicy is orthogonal — READONLY is allowed
        result = validate_quant_safety(workflow)
        assert result["safe"] is True
