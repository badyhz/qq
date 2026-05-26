"""Unit tests for core/schedule_safety.py — schedule-time safety gate."""
from __future__ import annotations

import pytest

from core.schedule_safety import (
    ScheduleSafetyGate,
    ScheduleValidationResult,
    ScheduleViolation,
)
from core.workflow_safety import WorkflowSafetyValidator


# ── helpers ──────────────────────────────────────────────────────────


@pytest.fixture
def gate() -> ScheduleSafetyGate:
    return ScheduleSafetyGate()


# ── allowed task passes ──────────────────────────────────────────────


class TestAllowedTaskPassesValidation:
    def test_safe_task_allowed(self, gate: ScheduleSafetyGate):
        r = gate.validate_dispatch("build_dashboard", "report")
        assert r.allowed is True
        assert len(r.violations) == 0
        assert r.passed_tasks == ["build_dashboard"]

    def test_safe_task_with_deps(self, gate: ScheduleSafetyGate):
        r = gate.validate_dispatch("run_tests", "validation", task_deps=["build_dashboard"])
        assert r.allowed is True


# ── blocked category ─────────────────────────────────────────────────


class TestBlockedCategory:
    def test_submit_blocked(self, gate: ScheduleSafetyGate):
        r = gate.validate_dispatch("task_1", "submit")
        assert r.allowed is False
        assert any(v.rule == "BLOCKED_CATEGORY" for v in r.violations)

    def test_live_execution_blocked(self, gate: ScheduleSafetyGate):
        r = gate.validate_dispatch("task_2", "live_execution")
        assert r.allowed is False

    def test_planner_escalation_blocked(self, gate: ScheduleSafetyGate):
        r = gate.validate_dispatch("task_3", "planner_escalation")
        assert r.allowed is False

    def test_all_default_categories_blocked(self, gate: ScheduleSafetyGate):
        blocked = {"submit", "cancel", "flatten", "live_execution",
                   "planner_escalation", "place_order", "close_position"}
        for cat in blocked:
            r = gate.validate_dispatch("x", cat)
            assert r.allowed is False


# ── blocked task_id pattern ──────────────────────────────────────────


class TestBlockedTaskIdPattern:
    def test_live_runner_blocked(self, gate: ScheduleSafetyGate):
        r = gate.validate_dispatch("run_live_runner_v2", "dispatch")
        assert r.allowed is False
        assert any(v.rule == "BLOCKED_TASK_PATTERN" for v in r.violations)

    def test_submit_order_blocked(self, gate: ScheduleSafetyGate):
        r = gate.validate_dispatch("submit_order_now", "dispatch")
        assert r.allowed is False

    def test_cancel_order_blocked(self, gate: ScheduleSafetyGate):
        r = gate.validate_dispatch("cancel_order_handler", "dispatch")
        assert r.allowed is False

    def test_flatten_position_blocked(self, gate: ScheduleSafetyGate):
        r = gate.validate_dispatch("flatten_position_safe", "dispatch")
        assert r.allowed is False

    def test_case_insensitive_match(self, gate: ScheduleSafetyGate):
        r = gate.validate_dispatch("LIVE_RUNNER_TEST", "dispatch")
        assert r.allowed is False


# ── multiple violations ──────────────────────────────────────────────


class TestMultipleViolations:
    def test_category_and_pattern(self, gate: ScheduleSafetyGate):
        r = gate.validate_dispatch("submit_order_batch", "submit")
        assert r.allowed is False
        rules = {v.rule for v in r.violations}
        assert "BLOCKED_CATEGORY" in rules
        assert "BLOCKED_TASK_PATTERN" in rules

    def test_two_patterns(self, gate: ScheduleSafetyGate):
        r = gate.validate_dispatch("flatten_position_submit_order", "dispatch")
        assert r.allowed is False
        rules = {v.rule for v in r.violations}
        assert "BLOCKED_TASK_PATTERN" in rules
        # both flatten_position and submit_order are substrings
        assert len(r.violations) >= 2


# ── batch validation ─────────────────────────────────────────────────


class TestBatchValidation:
    def test_all_allowed(self, gate: ScheduleSafetyGate):
        tasks = [
            {"task_id": "build_report", "category": "report"},
            {"task_id": "run_checks", "category": "validation"},
        ]
        r = gate.validate_batch(tasks)
        assert r.allowed is True
        assert r.blocked_tasks == []
        assert len(r.passed_tasks) == 2

    def test_mixed(self, gate: ScheduleSafetyGate):
        tasks = [
            {"task_id": "build_report", "category": "report"},
            {"task_id": "submit_batch", "category": "submit"},
            {"task_id": "run_checks", "category": "validation"},
        ]
        r = gate.validate_batch(tasks)
        assert r.allowed is False
        assert "submit_batch" in r.blocked_tasks
        assert "build_report" in r.passed_tasks
        assert "run_checks" in r.passed_tasks

    def test_empty_batch(self, gate: ScheduleSafetyGate):
        r = gate.validate_batch([])
        assert r.allowed is True
        assert r.violations == []
        assert r.blocked_tasks == []
        assert r.passed_tasks == []


# ── is_dispatchable ──────────────────────────────────────────────────


class TestIsDispatchable:
    def test_true(self, gate: ScheduleSafetyGate):
        assert gate.is_dispatchable("safe_task", "report") is True

    def test_false_category(self, gate: ScheduleSafetyGate):
        assert gate.is_dispatchable("task_1", "submit") is False

    def test_false_pattern(self, gate: ScheduleSafetyGate):
        assert gate.is_dispatchable("live_runner_main", "dispatch") is False


# ── add/remove blocked category ──────────────────────────────────────


class TestCategoryManagement:
    def test_add_blocks(self, gate: ScheduleSafetyGate):
        gate.add_blocked_category("backtest")
        assert gate.is_dispatchable("task_1", "backtest") is False

    def test_remove_unblocks(self, gate: ScheduleSafetyGate):
        gate.remove_blocked_category("submit")
        assert gate.is_dispatchable("task_1", "submit") is True

    def test_remove_nonexistent_no_error(self, gate: ScheduleSafetyGate):
        gate.remove_blocked_category("nonexistent_category")

    def test_add_reflected_in_summary(self, gate: ScheduleSafetyGate):
        gate.add_blocked_category("custom")
        s = gate.summary()
        assert "custom" in s["blocked_categories"]


# ── summary ──────────────────────────────────────────────────────────


class TestSummary:
    def test_counts(self, gate: ScheduleSafetyGate):
        gate.validate_dispatch("safe_task", "report")
        gate.validate_dispatch("submit_batch", "submit")
        gate.validate_dispatch("run_checks", "validation")
        s = gate.summary()
        assert s["total_checked"] == 3
        assert s["total_blocked"] == 1
        assert s["total_passed"] == 2

    def test_keys_present(self, gate: ScheduleSafetyGate):
        s = gate.summary()
        assert "total_checked" in s
        assert "total_blocked" in s
        assert "total_passed" in s
        assert "blocked_categories" in s
        assert "blocked_patterns" in s


# ── integration with workflow_safety ─────────────────────────────────


class TestWorkflowSafetyIntegration:
    def test_independent_operation(self, gate: ScheduleSafetyGate):
        wf = WorkflowSafetyValidator()

        # schedule gate blocks "submit" category
        sched_result = gate.validate_dispatch("task_1", "submit")
        assert sched_result.allowed is False

        # workflow validator blocks "live_runner" pattern
        wf_violations = wf.validate_task_id("live_runner_test")
        assert len(wf_violations) > 0

        # safe task passes both
        sched_ok = gate.validate_dispatch("build_report", "report")
        assert sched_ok.allowed is True

        wf_ok = wf.validate_task_id("safe_task")
        assert len(wf_ok) == 0

    def test_schedule_result_dataclass(self):
        v = ScheduleViolation(rule="TEST", severity="HIGH", detail="x", task_id="t1")
        r = ScheduleValidationResult(allowed=False, violations=[v], blocked_tasks=["t1"], passed_tasks=[])
        assert r.allowed is False
        assert r.violations[0].task_id == "t1"
