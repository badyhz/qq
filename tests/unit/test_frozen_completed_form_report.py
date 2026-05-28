"""Tests for frozen_completed_form_report.py — T16501."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.frozen_completed_form_report import (
    RELEASE_HOLD_REQUIRED,
    render_manifest,
    render_report_html,
    render_report_json,
    render_report_markdown,
)


@pytest.fixture
def sample_simulations():
    return {
        "simulations": [
            {
                "completed_form_id": "f1", "source_form_id": "s1", "path": "core/a.py",
                "simulation_category": "valid_keep_frozen",
                "reviewer_name": "Alice", "reviewer_role": "Analyst",
                "review_date": "2026-05-29", "human_decision": "KEEP_FROZEN",
                "decision_reason": "Keep.", "evidence_status": "COMPLETE",
                "evidence_ids_confirmed": [], "hash_evidence_confirmed": True,
                "rollback_evidence_confirmed": True, "backup_evidence_confirmed": True,
                "mandatory_confirmations_checked": [], "forbidden_confirmations_checked": [],
                "release_hold": "HOLD", "advisory_only": True, "human_review_required": True,
                "dry_run_only": True, "action_requested": False, "no_action_performed": True,
            },
        ],
        "total_count": 1,
        "category_counts": {"valid_keep_frozen": 1},
        "release_hold": "HOLD",
    }


@pytest.fixture
def sample_validation():
    return {
        "results": [
            {
                "completed_form_id": "f1", "source_form_id": "s1", "path": "core/a.py",
                "simulation_category": "valid_keep_frozen",
                "outcome": "DRY_RUN_ACCEPTED_PREPARE_ONLY", "reason": "OK",
                "action_authorized": False, "no_action_performed": True, "release_hold": "HOLD",
            },
            {
                "completed_form_id": "f2", "source_form_id": "s2", "path": "scripts/b.py",
                "simulation_category": "forbidden_delete_now",
                "outcome": "DRY_RUN_REJECTED_FORBIDDEN_DECISION", "reason": "forbidden",
                "action_authorized": False, "no_action_performed": True, "release_hold": "HOLD",
            },
            {
                "completed_form_id": "f3", "source_form_id": "s3", "path": "core/c.py",
                "simulation_category": "release_hold_override",
                "outcome": "DRY_RUN_REJECTED_RELEASE_HOLD_OVERRIDE", "reason": "override",
                "action_authorized": False, "no_action_performed": True, "release_hold": "RELEASED",
            },
            {
                "completed_form_id": "f4", "source_form_id": "s4", "path": "scripts/d.py",
                "simulation_category": "unsafe_auto_action",
                "outcome": "DRY_RUN_REJECTED_UNSAFE_ACTION_REQUEST", "reason": "unsafe",
                "action_authorized": False, "no_action_performed": True, "release_hold": "HOLD",
            },
            {
                "completed_form_id": "f5", "source_form_id": "s5", "path": "core/e.py",
                "simulation_category": "request_more_review",
                "outcome": "DRY_RUN_NEEDS_MORE_REVIEW", "reason": "more review",
                "action_authorized": False, "no_action_performed": True, "release_hold": "HOLD",
            },
            {
                "completed_form_id": "f6", "source_form_id": "s6", "path": "scripts/f.py",
                "simulation_category": "missing_evidence",
                "outcome": "DRY_RUN_REJECTED_MISSING_EVIDENCE", "reason": "incomplete",
                "action_authorized": False, "no_action_performed": True, "release_hold": "HOLD",
            },
        ],
        "total_count": 6,
        "outcome_counts": {
            "DRY_RUN_ACCEPTED_PREPARE_ONLY": 1,
            "DRY_RUN_REJECTED_FORBIDDEN_DECISION": 1,
            "DRY_RUN_REJECTED_RELEASE_HOLD_OVERRIDE": 1,
            "DRY_RUN_REJECTED_UNSAFE_ACTION_REQUEST": 1,
            "DRY_RUN_NEEDS_MORE_REVIEW": 1,
            "DRY_RUN_REJECTED_MISSING_EVIDENCE": 1,
        },
        "accepted_count": 1,
        "rejected_count": 4,
        "needs_review_count": 1,
        "release_hold": "HOLD",
    }


@pytest.fixture
def sample_matrix():
    return {
        "entries": [
            {
                "outcome": "DRY_RUN_ACCEPTED_PREPARE_ONLY",
                "count": 1, "affected_paths": ["core/a.py"],
                "example_form_ids": ["f1"],
                "allowed_next_manual_step": "Human may review.",
                "forbidden_next_actions": ["DELETE_NOW", "MOVE_NOW"],
                "requires_more_evidence": False, "requires_human_review": True,
                "action_authorized": False, "no_action_performed": True,
                "release_hold": "HOLD",
            },
        ],
        "total_forms": 6,
        "total_outcomes": 1,
        "release_hold": "HOLD",
        "action_authorized": False,
        "no_action_performed": True,
    }


class TestAllSectionsPresent:
    def test_all_sections(self, sample_simulations, sample_validation, sample_matrix):
        report = render_report_json(sample_simulations, sample_validation, sample_matrix)
        sections = report["sections"]
        expected = [
            "executive_summary", "safety_boundary", "simulation_scope",
            "completed_form_categories", "accepted_prepare_only",
            "rejected_forbidden_decisions", "rejected_missing_evidence",
            "release_hold_override_attempts", "unsafe_auto_action_requests",
            "outcome_matrix", "pending_human_review", "no_action_authorized_statement",
            "no_file_operation_statement", "forbidden_actions", "release_hold_statement",
            "next_safe_actions",
        ]
        for key in expected:
            assert key in sections, f"missing section: {key}"


class TestNoActivationRecommendation:
    def test_no_activation(self, sample_simulations, sample_validation, sample_matrix):
        report = render_report_json(sample_simulations, sample_validation, sample_matrix)
        md = render_report_markdown(report)
        assert "NO ACTION AUTHORIZED" in md


class TestNoDeleteMoveCopyArchive:
    def test_no_authorization(self, sample_simulations, sample_validation, sample_matrix):
        report = render_report_json(sample_simulations, sample_validation, sample_matrix)
        assert report["action_authorized"] is False
        assert report["no_action_performed"] is True


class TestReleaseHoldMismatch:
    def test_mismatch_fails(self, sample_simulations, sample_validation, sample_matrix):
        with pytest.raises(ValueError, match="release_hold"):
            render_report_json(sample_simulations, sample_validation, sample_matrix, release_hold="RELEASED")


class TestDeterministic:
    def test_deterministic(self, sample_simulations, sample_validation, sample_matrix):
        r1 = render_report_json(sample_simulations, sample_validation, sample_matrix)
        r2 = render_report_json(sample_simulations, sample_validation, sample_matrix)
        h1 = hashlib.sha256(json.dumps(r1, sort_keys=True).encode()).hexdigest()
        h2 = hashlib.sha256(json.dumps(r2, sort_keys=True).encode()).hexdigest()
        assert h1 == h2


class TestHTMLOffline:
    def test_html_standalone(self, sample_simulations, sample_validation, sample_matrix):
        report = render_report_json(sample_simulations, sample_validation, sample_matrix)
        html = render_report_html(report)
        assert "<!DOCTYPE html>" in html
        # No CDN or external JS
        assert "cdn" not in html.lower()
        assert "googleapis" not in html.lower()
        assert "cloudflare" not in html.lower()
        assert "<script src=" not in html


class TestRenderMarkdown:
    def test_markdown(self, sample_simulations, sample_validation, sample_matrix):
        report = render_report_json(sample_simulations, sample_validation, sample_matrix)
        md = render_report_markdown(report)
        assert "Frozen Completed Form Report" in md
        assert "release_hold" in md


class TestRenderManifest:
    def test_manifest(self, sample_simulations, sample_validation, sample_matrix):
        report = render_report_json(sample_simulations, sample_validation, sample_matrix)
        manifest = render_manifest(report)
        assert manifest["release_hold"] == "HOLD"
        assert manifest["action_authorized"] is False
        assert "report_hash" in manifest
