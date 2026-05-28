"""Tests for frozen_approval_validator.py — T16001."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.frozen_approval_validator import (
    ALLOWED_DECISIONS,
    FORBIDDEN_DECISIONS,
    RELEASE_HOLD_REQUIRED,
    ValidationReport,
    validate_completed_form,
    validate_forms,
    validate_template,
)


@pytest.fixture
def safe_template():
    return {
        "form_id": "approval_form_core__live_runner_py",
        "path": "core/live_runner.py",
        "form_type": "OFFLINE_REWRITE_APPROVAL_FORM",
        "reviewer_name": "PENDING_HUMAN_REVIEWER",
        "reviewer_role": "PENDING_HUMAN_ROLE",
        "review_date": "PENDING_HUMAN_DATE",
        "candidate_action": "PREPARE_OFFLINE_REWRITE",
        "required_evidence_ids": ["original_path_confirmed"],
        "required_evidence_paths": ["evidence/core__live_runner_py/hash_record.json"],
        "original_sha256": "5fe494dad7f7d379ece5c6966530f4d220df94d40ceeec820521df8a22519831",
        "original_size_bytes": 4202,
        "proposed_backup_path": "archive_simulation/frozen_files/core__live_runner_py",
        "proposed_archive_path": "archive_simulation/archived/core__live_runner_py",
        "rollback_plan_id": "rollback_sim_core__live_runner_py",
        "human_decision_placeholder": "PENDING_HUMAN_DECISION",
        "decision_reason_placeholder": "PENDING_HUMAN_REASON",
        "approval_conditions": ["all_evidence_collected", "release_hold_remains_HOLD"],
        "rejection_conditions": ["evidence_incomplete"],
        "mandatory_confirmations": [
            "I confirm this is offline-only.",
            "I confirm no file has been executed.",
            "I confirm no file has been imported.",
            "I confirm no file has been copied by automation.",
            "I confirm no file has been moved by automation.",
            "I confirm no file has been deleted by automation.",
            "I confirm release_hold remains HOLD.",
            "I confirm live/testnet/runtime remains disabled.",
            "I confirm backup/archive/delete still requires separate explicit human approval.",
        ],
        "forbidden_confirmations": [
            "approve_live_activation",
            "approve_testnet_activation",
            "approve_runtime_activation",
            "approve_immediate_delete",
            "approve_immediate_move",
            "approve_automated_backup",
            "approve_automated_archive",
        ],
        "signature_placeholder": "PENDING_HUMAN_SIGNATURE",
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
    }


class TestSafeTemplatesPass:
    def test_all_checks_pass(self, safe_template):
        checks = validate_template(safe_template, "HOLD")
        for check in checks:
            assert check.passed, f"{check.check_name}: {check.detail}"

    def test_full_report_passes(self, safe_template):
        report = validate_forms([safe_template], release_hold="HOLD")
        assert report.all_passed is True
        assert report.failed_checks == 0


class TestForbiddenImmediateDecision:
    def test_delete_now_fails(self, safe_template):
        form = {**safe_template, "human_decision_placeholder": "DELETE_NOW"}
        report = validate_forms([form], release_hold="HOLD")
        assert report.all_passed is False

    def test_move_now_fails(self, safe_template):
        form = {**safe_template, "human_decision_placeholder": "MOVE_NOW"}
        report = validate_forms([form], release_hold="HOLD")
        assert report.all_passed is False

    def test_archive_now_fails(self, safe_template):
        form = {**safe_template, "human_decision_placeholder": "ARCHIVE_NOW"}
        report = validate_forms([form], release_hold="HOLD")
        assert report.all_passed is False

    def test_activate_live_fails(self, safe_template):
        form = {**safe_template, "human_decision_placeholder": "ACTIVATE_LIVE"}
        report = validate_forms([form], release_hold="HOLD")
        assert report.all_passed is False


class TestCompletedFormMissingReviewer:
    def test_missing_reviewer_fails(self, safe_template):
        form = {
            **safe_template,
            "human_decision_placeholder": "KEEP_FROZEN",
            "reviewer_name": "PENDING_HUMAN_REVIEWER",
        }
        checks = validate_completed_form(form, "HOLD")
        reviewer_check = next(c for c in checks if "completed_reviewer" in c.check_name)
        assert reviewer_check.passed is False


class TestCompletedFormMissingDecision:
    def test_missing_decision_ok_when_placeholder(self, safe_template):
        # Still placeholder — no validation failure
        checks = validate_completed_form(safe_template, "HOLD")
        decision_check = next(c for c in checks if "completed_decision" in c.check_name)
        assert decision_check.passed is True


class TestCompletedFormForbiddenDecision:
    def test_forbidden_decision_fails(self, safe_template):
        form = {**safe_template, "human_decision_placeholder": "DELETE_NOW"}
        checks = validate_completed_form(form, "HOLD")
        decision_check = next(c for c in checks if "completed_decision" in c.check_name)
        assert decision_check.passed is False


class TestCompletedFormEvidenceRequired:
    def test_prepare_archive_needs_evidence(self, safe_template):
        """If decision is APPROVE_PREPARE_ARCHIVE_AFTER_BACKUP, evidence must be reviewed.
        Template validation passes; completed form validation checks reviewer."""
        form = {
            **safe_template,
            "human_decision_placeholder": "APPROVE_PREPARE_ARCHIVE_AFTER_BACKUP",
            "reviewer_name": "Alice",
        }
        checks = validate_completed_form(form, "HOLD")
        # Should pass if reviewer is set
        reviewer_check = next(c for c in checks if "completed_reviewer" in c.check_name)
        assert reviewer_check.passed is True


class TestReleaseHoldMismatch:
    def test_release_hold_mismatch_fails(self, safe_template):
        with pytest.raises(ValueError, match="release_hold"):
            validate_forms([safe_template], release_hold="RELEASED")


class TestDeterministic:
    def test_deterministic_output(self, safe_template):
        r1 = validate_forms([safe_template], release_hold="HOLD")
        r2 = validate_forms([safe_template], release_hold="HOLD")
        h1 = hashlib.sha256(json.dumps(r1.to_dict(), sort_keys=True).encode()).hexdigest()
        h2 = hashlib.sha256(json.dumps(r2.to_dict(), sort_keys=True).encode()).hexdigest()
        assert h1 == h2


import hashlib
