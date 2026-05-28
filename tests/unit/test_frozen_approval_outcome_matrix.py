"""Tests for frozen_approval_outcome_matrix.py — T16501."""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.frozen_approval_outcome_matrix import (
    FORBIDDEN_NEXT_ACTIONS,
    RELEASE_HOLD_REQUIRED,
    OutcomeEntry,
    OutcomeMatrix,
    build_outcome_matrix,
    render_manifest,
    render_matrix_markdown,
)


@pytest.fixture
def sample_results():
    return [
        {
            "completed_form_id": "f1", "source_form_id": "s1", "path": "core/a.py",
            "simulation_category": "valid_keep_frozen",
            "outcome": "DRY_RUN_ACCEPTED_PREPARE_ONLY", "reason": "OK",
            "action_authorized": False, "no_action_performed": True, "release_hold": "HOLD",
        },
        {
            "completed_form_id": "f2", "source_form_id": "s2", "path": "scripts/b.py",
            "simulation_category": "valid_prepare_archive",
            "outcome": "DRY_RUN_ACCEPTED_PREPARE_ONLY", "reason": "OK",
            "action_authorized": False, "no_action_performed": True, "release_hold": "HOLD",
        },
        {
            "completed_form_id": "f3", "source_form_id": "s3", "path": "core/c.py",
            "simulation_category": "forbidden_delete_now",
            "outcome": "DRY_RUN_REJECTED_FORBIDDEN_DECISION", "reason": "forbidden",
            "action_authorized": False, "no_action_performed": True, "release_hold": "HOLD",
        },
        {
            "completed_form_id": "f4", "source_form_id": "s4", "path": "scripts/d.py",
            "simulation_category": "request_more_review",
            "outcome": "DRY_RUN_NEEDS_MORE_REVIEW", "reason": "more review",
            "action_authorized": False, "no_action_performed": True, "release_hold": "HOLD",
        },
        {
            "completed_form_id": "f5", "source_form_id": "s5", "path": "core/e.py",
            "simulation_category": "missing_evidence",
            "outcome": "DRY_RUN_REJECTED_MISSING_EVIDENCE", "reason": "incomplete",
            "action_authorized": False, "no_action_performed": True, "release_hold": "HOLD",
        },
    ]


class TestOutcomeCounts:
    def test_correct_counts(self, sample_results):
        matrix = build_outcome_matrix(sample_results)
        counts = {e.outcome: e.count for e in matrix.entries}
        assert counts["DRY_RUN_ACCEPTED_PREPARE_ONLY"] == 2
        assert counts["DRY_RUN_REJECTED_FORBIDDEN_DECISION"] == 1
        assert counts["DRY_RUN_NEEDS_MORE_REVIEW"] == 1
        assert counts["DRY_RUN_REJECTED_MISSING_EVIDENCE"] == 1


class TestForbiddenNextActions:
    def test_forbidden_actions_included(self, sample_results):
        matrix = build_outcome_matrix(sample_results)
        for entry in matrix.entries:
            for action in FORBIDDEN_NEXT_ACTIONS:
                assert action in entry.forbidden_next_actions


class TestActionAuthorizedFalse:
    def test_all_entries_no_authorization(self, sample_results):
        matrix = build_outcome_matrix(sample_results)
        for entry in matrix.entries:
            assert entry.action_authorized is False
            assert entry.no_action_performed is True


class TestNoActionPerformed:
    def test_no_action_true(self, sample_results):
        matrix = build_outcome_matrix(sample_results)
        assert matrix.no_action_performed is True
        assert matrix.action_authorized is False


class TestReleaseHoldMismatch:
    def test_mismatch_fails(self, sample_results):
        with pytest.raises(ValueError, match="release_hold"):
            build_outcome_matrix(sample_results, release_hold="RELEASED")


class TestDeterministic:
    def test_deterministic(self, sample_results):
        m1 = build_outcome_matrix(sample_results)
        m2 = build_outcome_matrix(sample_results)
        h1 = hashlib.sha256(json.dumps(m1.to_dict(), sort_keys=True).encode()).hexdigest()
        h2 = hashlib.sha256(json.dumps(m2.to_dict(), sort_keys=True).encode()).hexdigest()
        assert h1 == h2


class TestRenderMarkdown:
    def test_render(self, sample_results):
        matrix = build_outcome_matrix(sample_results)
        md = render_matrix_markdown(matrix)
        assert "Frozen Approval Outcome Matrix" in md
        assert "NO ACTION AUTHORIZED" in md


class TestRenderManifest:
    def test_manifest(self, sample_results):
        matrix = build_outcome_matrix(sample_results)
        manifest = render_manifest(matrix)
        assert manifest["release_hold"] == "HOLD"
        assert manifest["action_authorized"] is False
        assert "matrix_hash" in manifest
