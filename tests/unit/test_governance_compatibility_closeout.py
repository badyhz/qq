from __future__ import annotations

import importlib

import pytest

ALL_GOVERNANCE_MODULES = [
    "core.dirty_workspace_action_recommendation",
    "core.dirty_workspace_classification_renderer",
    "core.dirty_workspace_classification_result",
    "core.dirty_workspace_duplicate_record",
    "core.dirty_workspace_duplicate_report_renderer",
    "core.dirty_workspace_file_category",
    "core.dirty_workspace_file_record",
    "core.dirty_workspace_freeze_violation",
    "core.dirty_workspace_freeze_violation_renderer",
    "core.dirty_workspace_governance",
    "core.dirty_workspace_governance_renderer",
    "core.dirty_workspace_governance_verdict",
    "core.dirty_workspace_model_closeout",
    "core.dirty_workspace_risk_level",
    "core.freeze_aware_admission_result",
    "core.freeze_aware_denial_reason",
    "core.freeze_aware_dependency_result",
    "core.freeze_aware_handoff_packet",
    "core.freeze_aware_hold_state",
    "core.freeze_aware_queue",
    "core.freeze_aware_queue_closeout_renderer",
    "core.freeze_aware_queue_model_closeout",
    "core.freeze_aware_queue_renderer",
    "core.freeze_aware_queue_verdict",
    "core.freeze_aware_task_state",
    "core.freeze_aware_transition_guard",
    "core.human_review_approval_state",
    "core.human_review_checklist_renderer",
    "core.human_review_decision",
    "core.human_review_escalation_rule",
    "core.human_review_evidence_checklist",
    "core.human_review_evidence_packet_renderer",
    "core.human_review_forbidden_approval",
    "core.human_review_gate",
    "core.human_review_gate_model_closeout",
    "core.human_review_gate_renderer",
    "core.human_review_gate_verdict",
    "core.human_review_rejection_state",
    "core.human_review_rollback_requirement",
    "core.human_review_verdict_renderer",
]


def test_all_40_governance_modules_import() -> None:
    errors: list[str] = []
    for mod_name in ALL_GOVERNANCE_MODULES:
        try:
            mod = importlib.import_module(mod_name)
            assert mod is not None, f"Module {mod_name} imported as None"
        except ImportError as exc:
            errors.append(f"{mod_name}: {exc}")
    assert not errors, f"Import failures:\n" + "\n".join(errors)
    assert len(ALL_GOVERNANCE_MODULES) == 40, (
        f"Expected 40 modules, got {len(ALL_GOVERNANCE_MODULES)}"
    )


def test_module_count_is_40() -> None:
    assert len(ALL_GOVERNANCE_MODULES) == 40
