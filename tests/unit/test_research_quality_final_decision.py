"""Tests for research quality final decision — T8801-T8840.

Full pass, targeted-only partial, missing CLI fail tests.
"""
from __future__ import annotations

import pytest
from core.research_quality_final_decision import evaluate_final_decision, final_decision_to_dict


class TestFinalDecisionNormal:
    def test_full_pass(self):
        d = evaluate_final_decision(
            full_suite_passed=True, workbench_acceptance_passed=True,
            quality_gate_passed=True, rerun_passed=True,
            comparator_passed=True, closeout_generated=True,
            all_artifacts_present=True,
        )
        assert d.verdict == "PASS"
        assert d.required_commands_passed is True

    def test_pass_requires_safety(self):
        d = evaluate_final_decision(
            full_suite_passed=True, workbench_acceptance_passed=True,
            quality_gate_passed=True, rerun_passed=True,
            comparator_passed=True, closeout_generated=True,
            all_artifacts_present=True, release_hold_is_hold=False,
        )
        assert d.verdict == "FAIL"


class TestFinalDecisionEdge:
    def test_partial_missing_suite(self):
        d = evaluate_final_decision(
            full_suite_passed=False, workbench_acceptance_passed=True,
            quality_gate_passed=True, rerun_passed=True,
            comparator_passed=True, closeout_generated=True,
            all_artifacts_present=True,
        )
        assert d.verdict == "PARTIAL"


class TestFinalDecisionAdversarial:
    def test_fail_missing_artifacts(self):
        d = evaluate_final_decision(
            full_suite_passed=True, workbench_acceptance_passed=True,
            quality_gate_passed=True, rerun_passed=True,
            comparator_passed=True, closeout_generated=True,
            all_artifacts_present=False,
        )
        assert d.verdict == "FAIL"

    def test_fail_non_hold(self):
        d = evaluate_final_decision(
            full_suite_passed=True, workbench_acceptance_passed=True,
            quality_gate_passed=True, rerun_passed=True,
            comparator_passed=True, closeout_generated=True,
            all_artifacts_present=True, release_hold_is_hold=False,
        )
        assert d.verdict == "FAIL"


class TestFinalDecisionDeterministic:
    def test_deterministic(self):
        args = dict(full_suite_passed=True, workbench_acceptance_passed=True,
                    quality_gate_passed=True, rerun_passed=True,
                    comparator_passed=True, closeout_generated=True,
                    all_artifacts_present=True)
        d1 = final_decision_to_dict(evaluate_final_decision(**args))
        d2 = final_decision_to_dict(evaluate_final_decision(**args))
        assert d1 == d2


class TestFinalDecisionSafetyBoundary:
    def test_safety_holds(self):
        d = evaluate_final_decision(
            full_suite_passed=True, workbench_acceptance_passed=True,
            quality_gate_passed=True, rerun_passed=True,
            comparator_passed=True, closeout_generated=True,
            all_artifacts_present=True,
        )
        assert d.safety_holds is True
