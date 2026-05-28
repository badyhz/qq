"""Tests for frozen_approval_dry_run_validator.py — T16501."""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.frozen_approval_dry_run_validator import (
    DRY_RUN_ACCEPTED_PREPARE_ONLY,
    DRY_RUN_NEEDS_MORE_REVIEW,
    DRY_RUN_REJECTED,
    DRY_RUN_REJECTED_CONFLICTING_CONFIRMATIONS,
    DRY_RUN_REJECTED_FORBIDDEN_DECISION,
    DRY_RUN_REJECTED_MISSING_DECISION,
    DRY_RUN_REJECTED_MISSING_EVIDENCE,
    DRY_RUN_REJECTED_MISSING_REVIEWER,
    DRY_RUN_REJECTED_RELEASE_HOLD_OVERRIDE,
    DRY_RUN_REJECTED_UNSAFE_ACTION_REQUEST,
    RELEASE_HOLD_REQUIRED,
    DryRunValidation,
    FormValidation,
    render_manifest,
    render_validation_markdown,
    validate_forms,
)


@pytest.fixture
def valid_keep_frozen():
    return {
        "completed_form_id": "completed_form_1",
        "source_form_id": "form_1",
        "path": "core/live_runner.py",
        "simulation_category": "valid_keep_frozen",
        "reviewer_name": "Alice",
        "reviewer_role": "Analyst",
        "review_date": "2026-05-29",
        "human_decision": "KEEP_FROZEN",
        "decision_reason": "Keep frozen.",
        "evidence_status": "COMPLETE_FOR_HUMAN_REVIEW",
        "evidence_ids_confirmed": ["e1"],
        "hash_evidence_confirmed": True,
        "rollback_evidence_confirmed": True,
        "backup_evidence_confirmed": True,
        "mandatory_confirmations_checked": ["conf1"],
        "forbidden_confirmations_checked": [],
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
        "dry_run_only": True,
        "action_requested": False,
        "no_action_performed": True,
    }


@pytest.fixture
def valid_prepare_archive():
    return {
        "completed_form_id": "completed_form_2",
        "source_form_id": "form_2",
        "path": "scripts/test.py",
        "simulation_category": "valid_prepare_archive_after_backup",
        "reviewer_name": "Bob",
        "reviewer_role": "Risk Officer",
        "review_date": "2026-05-29",
        "human_decision": "APPROVE_PREPARE_ARCHIVE_AFTER_BACKUP",
        "decision_reason": "Prepare archive.",
        "evidence_status": "COMPLETE_FOR_HUMAN_REVIEW",
        "evidence_ids_confirmed": ["e1", "e2"],
        "hash_evidence_confirmed": True,
        "rollback_evidence_confirmed": True,
        "backup_evidence_confirmed": True,
        "mandatory_confirmations_checked": ["conf1"],
        "forbidden_confirmations_checked": [],
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
        "dry_run_only": True,
        "action_requested": False,
        "no_action_performed": True,
    }


@pytest.fixture
def valid_prepare_delete():
    return {
        "completed_form_id": "completed_form_3",
        "source_form_id": "form_3",
        "path": "scripts/test3.py",
        "simulation_category": "valid_prepare_delete_after_backup",
        "reviewer_name": "Carol",
        "reviewer_role": "Compliance Officer",
        "review_date": "2026-05-29",
        "human_decision": "APPROVE_PREPARE_DELETE_AFTER_BACKUP",
        "decision_reason": "Prepare delete.",
        "evidence_status": "COMPLETE_FOR_HUMAN_REVIEW",
        "evidence_ids_confirmed": ["e1", "e2"],
        "hash_evidence_confirmed": True,
        "rollback_evidence_confirmed": True,
        "backup_evidence_confirmed": True,
        "mandatory_confirmations_checked": ["conf1"],
        "forbidden_confirmations_checked": [],
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
        "dry_run_only": True,
        "action_requested": False,
        "no_action_performed": True,
    }


@pytest.fixture
def valid_prepare_rewrite():
    return {
        "completed_form_id": "completed_form_4",
        "source_form_id": "form_4",
        "path": "scripts/test2.py",
        "simulation_category": "valid_prepare_offline_rewrite",
        "reviewer_name": "Dave",
        "reviewer_role": "Tech Lead",
        "review_date": "2026-05-29",
        "human_decision": "APPROVE_PREPARE_OFFLINE_REWRITE",
        "decision_reason": "Prepare rewrite.",
        "evidence_status": "COMPLETE_FOR_HUMAN_REVIEW",
        "evidence_ids_confirmed": ["e1"],
        "hash_evidence_confirmed": True,
        "rollback_evidence_confirmed": True,
        "backup_evidence_confirmed": True,
        "mandatory_confirmations_checked": ["conf1"],
        "forbidden_confirmations_checked": [],
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
        "dry_run_only": True,
        "action_requested": False,
        "no_action_performed": True,
    }


class TestValidKeepFrozenAccepted:
    def test_accepted_prepare_only(self, valid_keep_frozen):
        result = validate_forms([valid_keep_frozen])
        assert result.accepted_count == 1
        assert result.results[0].outcome == DRY_RUN_ACCEPTED_PREPARE_ONLY
        assert result.results[0].action_authorized is False


class TestValidPrepareArchiveAccepted:
    def test_accepted_prepare_only(self, valid_prepare_archive):
        result = validate_forms([valid_prepare_archive])
        assert result.accepted_count == 1
        assert result.results[0].outcome == DRY_RUN_ACCEPTED_PREPARE_ONLY
        assert result.results[0].action_authorized is False


class TestValidPrepareDeleteAccepted:
    def test_accepted_prepare_only(self):
        form = {
            "completed_form_id": "f3", "source_form_id": "s3", "path": "p3",
            "simulation_category": "valid",
            "reviewer_name": "Carol", "reviewer_role": "Officer",
            "review_date": "2026-05-29",
            "human_decision": "APPROVE_PREPARE_DELETE_AFTER_BACKUP",
            "decision_reason": "OK",
            "evidence_status": "COMPLETE_FOR_HUMAN_REVIEW",
            "evidence_ids_confirmed": [], "hash_evidence_confirmed": True,
            "rollback_evidence_confirmed": True, "backup_evidence_confirmed": True,
            "mandatory_confirmations_checked": [], "forbidden_confirmations_checked": [],
            "release_hold": "HOLD", "advisory_only": True, "human_review_required": True,
            "dry_run_only": True, "action_requested": False, "no_action_performed": True,
        }
        result = validate_forms([form])
        assert result.accepted_count == 1
        assert result.results[0].action_authorized is False


class TestValidPrepareRewriteAccepted:
    def test_accepted_prepare_only(self, valid_prepare_rewrite):
        result = validate_forms([valid_prepare_rewrite])
        assert result.accepted_count == 1
        assert result.results[0].action_authorized is False


class TestRequestMoreReview:
    def test_needs_more_review(self):
        form = {
            "completed_form_id": "f4", "source_form_id": "s4", "path": "p4",
            "simulation_category": "request_more_review",
            "reviewer_name": "Eve", "reviewer_role": "Audit",
            "review_date": "2026-05-29",
            "human_decision": "REQUEST_MORE_REVIEW",
            "decision_reason": "Need more.",
            "evidence_status": "PARTIAL", "evidence_ids_confirmed": [],
            "hash_evidence_confirmed": False, "rollback_evidence_confirmed": False,
            "backup_evidence_confirmed": False, "mandatory_confirmations_checked": [],
            "forbidden_confirmations_checked": [], "release_hold": "HOLD",
            "advisory_only": True, "human_review_required": True,
            "dry_run_only": True, "action_requested": False, "no_action_performed": True,
        }
        result = validate_forms([form])
        assert result.results[0].outcome == DRY_RUN_NEEDS_MORE_REVIEW
        assert result.results[0].action_authorized is False


class TestReject:
    def test_rejected(self):
        form = {
            "completed_form_id": "f5", "source_form_id": "s5", "path": "p5",
            "simulation_category": "reject",
            "reviewer_name": "Frank", "reviewer_role": "Gov",
            "review_date": "2026-05-29",
            "human_decision": "REJECT", "decision_reason": "No.",
            "evidence_status": "PARTIAL", "evidence_ids_confirmed": [],
            "hash_evidence_confirmed": False, "rollback_evidence_confirmed": False,
            "backup_evidence_confirmed": False, "mandatory_confirmations_checked": [],
            "forbidden_confirmations_checked": [], "release_hold": "HOLD",
            "advisory_only": True, "human_review_required": True,
            "dry_run_only": True, "action_requested": False, "no_action_performed": True,
        }
        result = validate_forms([form])
        assert result.results[0].outcome == DRY_RUN_REJECTED
        assert result.results[0].action_authorized is False


class TestForbiddenDecisions:
    @pytest.mark.parametrize("decision", [
        "DELETE_NOW", "MOVE_NOW", "COPY_NOW", "ARCHIVE_NOW",
        "EXECUTE_NOW", "IMPORT_NOW", "ACTIVATE_LIVE", "ACTIVATE_TESTNET",
        "ENABLE_RUNTIME", "ENABLE_PLANNER",
    ])
    def test_forbidden_rejected(self, decision):
        form = {
            "completed_form_id": "f_forbidden", "source_form_id": "s", "path": "p",
            "simulation_category": "forbidden",
            "reviewer_name": "Hank", "reviewer_role": "Bad",
            "review_date": "2026-05-29",
            "human_decision": decision, "decision_reason": "Want it.",
            "evidence_status": "COMPLETE_FOR_HUMAN_REVIEW", "evidence_ids_confirmed": [],
            "hash_evidence_confirmed": True, "rollback_evidence_confirmed": True,
            "backup_evidence_confirmed": True, "mandatory_confirmations_checked": [],
            "forbidden_confirmations_checked": [], "release_hold": "HOLD",
            "advisory_only": True, "human_review_required": True,
            "dry_run_only": True, "action_requested": False, "no_action_performed": True,
        }
        result = validate_forms([form])
        assert result.results[0].outcome == DRY_RUN_REJECTED_FORBIDDEN_DECISION
        assert result.results[0].action_authorized is False


class TestMissingReviewer:
    def test_missing_reviewer_rejected(self):
        form = {
            "completed_form_id": "f_mr", "source_form_id": "s", "path": "p",
            "simulation_category": "missing_reviewer",
            "reviewer_name": "", "reviewer_role": "",
            "review_date": "", "human_decision": "KEEP_FROZEN",
            "decision_reason": "Keep.", "evidence_status": "COMPLETE",
            "evidence_ids_confirmed": [], "hash_evidence_confirmed": True,
            "rollback_evidence_confirmed": True, "backup_evidence_confirmed": True,
            "mandatory_confirmations_checked": [], "forbidden_confirmations_checked": [],
            "release_hold": "HOLD", "advisory_only": True, "human_review_required": True,
            "dry_run_only": True, "action_requested": False, "no_action_performed": True,
        }
        result = validate_forms([form])
        assert result.results[0].outcome == DRY_RUN_REJECTED_MISSING_REVIEWER


class TestMissingDecision:
    def test_missing_decision_rejected(self):
        form = {
            "completed_form_id": "f_md", "source_form_id": "s", "path": "p",
            "simulation_category": "missing_decision",
            "reviewer_name": "Grace", "reviewer_role": "Analyst",
            "review_date": "2026-05-29", "human_decision": "",
            "decision_reason": "", "evidence_status": "PARTIAL",
            "evidence_ids_confirmed": [], "hash_evidence_confirmed": False,
            "rollback_evidence_confirmed": False, "backup_evidence_confirmed": False,
            "mandatory_confirmations_checked": [], "forbidden_confirmations_checked": [],
            "release_hold": "HOLD", "advisory_only": True, "human_review_required": True,
            "dry_run_only": True, "action_requested": False, "no_action_performed": True,
        }
        result = validate_forms([form])
        assert result.results[0].outcome == DRY_RUN_REJECTED_MISSING_DECISION


class TestReleaseHoldOverride:
    def test_release_hold_override_rejected(self):
        form = {
            "completed_form_id": "f_rh", "source_form_id": "s", "path": "p",
            "simulation_category": "release_hold_override",
            "reviewer_name": "Ivy", "reviewer_role": "Bad",
            "review_date": "2026-05-29", "human_decision": "KEEP_FROZEN",
            "decision_reason": "Override.", "evidence_status": "COMPLETE",
            "evidence_ids_confirmed": [], "hash_evidence_confirmed": True,
            "rollback_evidence_confirmed": True, "backup_evidence_confirmed": True,
            "mandatory_confirmations_checked": [], "forbidden_confirmations_checked": [],
            "release_hold": "RELEASED", "advisory_only": True, "human_review_required": True,
            "dry_run_only": True, "action_requested": False, "no_action_performed": True,
        }
        result = validate_forms([form])
        assert result.results[0].outcome == DRY_RUN_REJECTED_RELEASE_HOLD_OVERRIDE


class TestMissingEvidence:
    def test_missing_evidence_rejected(self):
        form = {
            "completed_form_id": "f_me", "source_form_id": "s", "path": "p",
            "simulation_category": "missing_evidence",
            "reviewer_name": "Jack", "reviewer_role": "Risk",
            "review_date": "2026-05-29",
            "human_decision": "APPROVE_PREPARE_ARCHIVE_AFTER_BACKUP",
            "decision_reason": "Want archive.", "evidence_status": "PENDING",
            "evidence_ids_confirmed": [], "hash_evidence_confirmed": False,
            "rollback_evidence_confirmed": False, "backup_evidence_confirmed": False,
            "mandatory_confirmations_checked": [], "forbidden_confirmations_checked": [],
            "release_hold": "HOLD", "advisory_only": True, "human_review_required": True,
            "dry_run_only": True, "action_requested": False, "no_action_performed": True,
        }
        result = validate_forms([form])
        assert result.results[0].outcome == DRY_RUN_REJECTED_MISSING_EVIDENCE


class TestConflictingConfirmations:
    def test_conflicting_rejected(self):
        form = {
            "completed_form_id": "f_cc", "source_form_id": "s", "path": "p",
            "simulation_category": "conflicting",
            "reviewer_name": "Nora", "reviewer_role": "Compliance",
            "review_date": "2026-05-29", "human_decision": "KEEP_FROZEN",
            "decision_reason": "Conflict.", "evidence_status": "COMPLETE",
            "evidence_ids_confirmed": [], "hash_evidence_confirmed": True,
            "rollback_evidence_confirmed": True, "backup_evidence_confirmed": True,
            "mandatory_confirmations_checked": ["approve_live_activation"],
            "forbidden_confirmations_checked": ["approve_live_activation"],
            "release_hold": "HOLD", "advisory_only": True, "human_review_required": True,
            "dry_run_only": True, "action_requested": False, "no_action_performed": True,
        }
        result = validate_forms([form])
        assert result.results[0].outcome == DRY_RUN_REJECTED_CONFLICTING_CONFIRMATIONS


class TestUnsafeAutoAction:
    def test_unsafe_rejected(self):
        form = {
            "completed_form_id": "f_ua", "source_form_id": "s", "path": "p",
            "simulation_category": "unsafe",
            "reviewer_name": "Oscar", "reviewer_role": "Script",
            "review_date": "2026-05-29", "human_decision": "KEEP_FROZEN",
            "decision_reason": "Auto.", "evidence_status": "COMPLETE",
            "evidence_ids_confirmed": [], "hash_evidence_confirmed": True,
            "rollback_evidence_confirmed": True, "backup_evidence_confirmed": True,
            "mandatory_confirmations_checked": [], "forbidden_confirmations_checked": [],
            "release_hold": "HOLD", "advisory_only": True, "human_review_required": True,
            "dry_run_only": True, "action_requested": True, "no_action_performed": True,
        }
        result = validate_forms([form])
        assert result.results[0].outcome == DRY_RUN_REJECTED_UNSAFE_ACTION_REQUEST


class TestAcceptedNeverAuthorizesAction:
    def test_accepted_never_authorizes(self, valid_keep_frozen):
        result = validate_forms([valid_keep_frozen])
        for r in result.results:
            assert r.action_authorized is False


class TestDeterministic:
    def test_deterministic(self, valid_keep_frozen):
        r1 = validate_forms([valid_keep_frozen])
        r2 = validate_forms([valid_keep_frozen])
        h1 = hashlib.sha256(json.dumps(r1.to_dict(), sort_keys=True).encode()).hexdigest()
        h2 = hashlib.sha256(json.dumps(r2.to_dict(), sort_keys=True).encode()).hexdigest()
        assert h1 == h2


class TestReleaseHoldMismatch:
    def test_mismatch_fails(self, valid_keep_frozen):
        with pytest.raises(ValueError, match="release_hold"):
            validate_forms([valid_keep_frozen], release_hold="RELEASED")
