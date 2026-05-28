"""Tests for frozen_manual_approval_form.py — T16001."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.frozen_manual_approval_form import (
    FORBIDDEN_CONFIRMATIONS,
    FORM_TYPES,
    MANDATORY_CONFIRMATIONS,
    RELEASE_HOLD_REQUIRED,
    ManualApprovalForm,
    build_form_from_checklist_item,
    build_manual_approval_forms,
    compute_forms_hash,
)

FIXTURE_DIR = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "frozen_manual_approval_form"


@pytest.fixture
def sample_checklist():
    return json.loads((FIXTURE_DIR / "sample_checklist.json").read_text())


class TestAllFormsHavePlaceholders:
    def test_decision_is_placeholder(self, sample_checklist):
        forms = build_manual_approval_forms(sample_checklist)
        for form in forms:
            assert form.human_decision_placeholder == "PENDING_HUMAN_DECISION"

    def test_reviewer_is_placeholder(self, sample_checklist):
        forms = build_manual_approval_forms(sample_checklist)
        for form in forms:
            assert form.reviewer_name == "PENDING_HUMAN_REVIEWER"

    def test_signature_is_placeholder(self, sample_checklist):
        forms = build_manual_approval_forms(sample_checklist)
        for form in forms:
            assert form.signature_placeholder == "PENDING_HUMAN_SIGNATURE"


class TestMandatoryConfirmationsPresent:
    def test_all_mandatory_confirmations(self, sample_checklist):
        forms = build_manual_approval_forms(sample_checklist)
        for form in forms:
            for mc in MANDATORY_CONFIRMATIONS:
                assert mc in form.mandatory_confirmations, f"missing: {mc}"


class TestForbiddenConfirmations:
    def test_forbidden_present(self, sample_checklist):
        forms = build_manual_approval_forms(sample_checklist)
        for form in forms:
            for fc in FORBIDDEN_CONFIRMATIONS:
                assert fc in form.forbidden_confirmations, f"missing forbidden: {fc}"

    def test_forbidden_not_in_mandatory(self, sample_checklist):
        forms = build_manual_approval_forms(sample_checklist)
        for form in forms:
            for fc in FORBIDDEN_CONFIRMATIONS:
                assert fc not in form.mandatory_confirmations


class TestNoImmediateActionGranted:
    def test_no_form_grants_immediate_delete(self, sample_checklist):
        forms = build_manual_approval_forms(sample_checklist)
        for form in forms:
            assert form.human_decision_placeholder != "DELETE_NOW"
            assert form.human_decision_placeholder != "APPROVED"

    def test_no_form_grants_immediate_move(self, sample_checklist):
        forms = build_manual_approval_forms(sample_checklist)
        for form in forms:
            assert form.human_decision_placeholder != "MOVE_NOW"

    def test_no_form_grants_immediate_copy(self, sample_checklist):
        forms = build_manual_approval_forms(sample_checklist)
        for form in forms:
            assert form.human_decision_placeholder != "COPY_NOW"

    def test_no_form_grants_immediate_archive(self, sample_checklist):
        forms = build_manual_approval_forms(sample_checklist)
        for form in forms:
            assert form.human_decision_placeholder != "ARCHIVE_NOW"


class TestFormTypes:
    def test_form_types_valid(self, sample_checklist):
        forms = build_manual_approval_forms(sample_checklist)
        for form in forms:
            assert form.form_type in FORM_TYPES

    def test_rewrite_form_type(self, sample_checklist):
        forms = build_manual_approval_forms(sample_checklist)
        rewrite = next(f for f in forms if f.candidate_action == "PREPARE_OFFLINE_REWRITE")
        assert rewrite.form_type == "OFFLINE_REWRITE_APPROVAL_FORM"

    def test_archive_form_type(self, sample_checklist):
        forms = build_manual_approval_forms(sample_checklist)
        archive = next(f for f in forms if f.candidate_action == "PREPARE_ARCHIVE_AFTER_BACKUP")
        assert archive.form_type == "ARCHIVE_AFTER_BACKUP_APPROVAL_FORM"


class TestReleaseHoldMismatch:
    def test_release_hold_mismatch_fails(self, sample_checklist):
        with pytest.raises(ValueError, match="release_hold"):
            build_manual_approval_forms(sample_checklist, release_hold="RELEASED")


class TestDeterministic:
    def test_deterministic_output(self, sample_checklist):
        forms1 = build_manual_approval_forms(sample_checklist)
        forms2 = build_manual_approval_forms(sample_checklist)
        assert compute_forms_hash(forms1) == compute_forms_hash(forms2)


class TestSafetyFlags:
    def test_all_forms_hold_and_advisory(self, sample_checklist):
        forms = build_manual_approval_forms(sample_checklist)
        for form in forms:
            assert form.release_hold == "HOLD"
            assert form.advisory_only is True
            assert form.human_review_required is True


class TestApprovalConditions:
    def test_approval_conditions_present(self, sample_checklist):
        forms = build_manual_approval_forms(sample_checklist)
        for form in forms:
            assert len(form.approval_conditions) > 0
            assert "release_hold_remains_HOLD" in form.approval_conditions

    def test_rejection_conditions_present(self, sample_checklist):
        forms = build_manual_approval_forms(sample_checklist)
        for form in forms:
            assert len(form.rejection_conditions) > 0
