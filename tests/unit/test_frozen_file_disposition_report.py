"""Tests for frozen file disposition report — T15001."""
from __future__ import annotations

import json
import pathlib
import tempfile

import pytest

from core.frozen_file_disposition_report import (
    RELEASE_HOLD_REQUIRED,
    build_report,
    render_html,
    render_markdown,
    write_html,
    write_json,
    write_manifest,
    write_markdown,
)

# Minimal test data
SAMPLE_QUEUE = [
    {
        "queue_id": "QR-0001",
        "path": "scripts/submit_approved_candidates.py",
        "exists": True,
        "category": "LIVE",
        "risk_score": 53,
        "risk_keywords": ["submit", "live"],
        "disposition": "CANDIDATE_FOR_ARCHIVE",
        "priority": "P0_CRITICAL_REVIEW",
        "reviewer_role": "senior_operator",
        "required_questions": ["Is file still needed?"],
        "required_evidence": ["file_hash_snapshot"],
        "possible_decisions": ["KEEP_FROZEN"],
        "forbidden_decisions": ["EXECUTE"],
        "recommended_default_action": "KEEP_FROZEN",
        "no_touch_required": True,
        "no_execution": True,
        "no_import": True,
        "no_stage": True,
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
    },
    {
        "queue_id": "QR-0002",
        "path": "scripts/run_testnet_order_smoke.py",
        "exists": True,
        "category": "LIVE",
        "risk_score": 63,
        "risk_keywords": ["testnet", "order"],
        "disposition": "CANDIDATE_FOR_REWRITE",
        "priority": "P1_HIGH_REVIEW",
        "reviewer_role": "operator",
        "required_questions": ["Is file still needed?"],
        "required_evidence": ["file_hash_snapshot"],
        "possible_decisions": ["KEEP_FROZEN"],
        "forbidden_decisions": ["EXECUTE"],
        "recommended_default_action": "KEEP_FROZEN",
        "no_touch_required": True,
        "no_execution": True,
        "no_import": True,
        "no_stage": True,
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
    },
    {
        "queue_id": "QR-0003",
        "path": "research/sample.md",
        "exists": True,
        "category": "UNKNOWN",
        "risk_score": 0,
        "risk_keywords": [],
        "disposition": "NEEDS_HUMAN_REVIEW",
        "priority": "UNKNOWN_REVIEW",
        "reviewer_role": "operator",
        "required_questions": [],
        "required_evidence": [],
        "possible_decisions": ["KEEP_FROZEN"],
        "forbidden_decisions": ["EXECUTE"],
        "recommended_default_action": "NEEDS_MORE_REVIEW",
        "no_touch_required": True,
        "no_execution": True,
        "no_import": True,
        "no_stage": True,
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
    },
]

SAMPLE_PREP = [
    {
        "path": "scripts/submit_approved_candidates.py",
        "priority": "P0_CRITICAL_REVIEW",
        "current_disposition": "CANDIDATE_FOR_ARCHIVE",
        "candidate_action": "PREPARE_ARCHIVE_AFTER_BACKUP",
        "backup_required": True,
        "backup_method": "manual_copy_to_secure_location",
        "deletion_allowed_now": False,
        "archive_allowed_now": False,
        "rewrite_allowed_now": False,
        "required_human_approval": True,
        "required_backup_evidence": ["sha256_hash_of_file", "backup_location_recorded"],
        "required_diff_review": True,
        "required_owner_note": True,
        "rollback_plan": "Restore from verified backup.",
        "final_manual_decision_placeholder": "AWAITING_HUMAN_DECISION",
        "no_touch_until_approved": True,
    },
    {
        "path": "scripts/run_testnet_order_smoke.py",
        "priority": "P1_HIGH_REVIEW",
        "current_disposition": "CANDIDATE_FOR_REWRITE",
        "candidate_action": "PREPARE_OFFLINE_REWRITE",
        "backup_required": True,
        "backup_method": "manual_copy_to_secure_location",
        "deletion_allowed_now": False,
        "archive_allowed_now": False,
        "rewrite_allowed_now": False,
        "required_human_approval": True,
        "required_backup_evidence": ["sha256_hash_of_file"],
        "required_diff_review": True,
        "required_owner_note": True,
        "rollback_plan": "Revert to frozen version from backup.",
        "final_manual_decision_placeholder": "AWAITING_HUMAN_DECISION",
        "no_touch_until_approved": True,
    },
]


class TestReportSections:
    def test_all_sections_present(self):
        report = build_report(SAMPLE_QUEUE, SAMPLE_PREP, release_hold="HOLD")
        md = render_markdown(report)
        expected_sections = [
            "Executive Summary",
            "Safety Boundary",
            "Frozen File Count",
            "Priority Breakdown",
            "Disposition Breakdown",
            "P0 Critical Review Items",
            "P1 High Review Items",
            "Archive Candidates",
            "Delete After Backup Candidates",
            "Offline Rewrite Candidates",
            "Keep Frozen Items",
            "Unknown Items",
            "Required Human Decisions",
            "Required Backup Evidence",
            "Forbidden Actions",
            "No-Touch Statement",
            "release_hold HOLD Statement",
            "Next Safe Actions",
        ]
        for section in expected_sections:
            assert section in md, f"Missing section: {section}"


class TestNoTouchStatement:
    def test_no_touch_present(self):
        report = build_report(SAMPLE_QUEUE, SAMPLE_PREP, release_hold="HOLD")
        md = render_markdown(report)
        assert "No-Touch Statement" in md
        assert "release_hold is HOLD" in md


class TestHTML:
    def test_html_generated_offline(self):
        report = build_report(SAMPLE_QUEUE, SAMPLE_PREP, release_hold="HOLD")
        html = render_html(report)
        assert "<!DOCTYPE html>" in html
        # No CDN or external JS
        assert "cdn" not in html.lower()
        assert "googleapis" not in html.lower()
        assert "<script src=" not in html


class TestNoActivationRecommendation:
    def test_no_activation(self):
        report = build_report(SAMPLE_QUEUE, SAMPLE_PREP, release_hold="HOLD")
        md = render_markdown(report)
        forbidden = ["ACTIVATE_LIVE", "ACTIVATE_TESTNET", "EXECUTE_NOW", "DELETE_NOW"]
        for action in forbidden:
            assert action in md  # Listed as forbidden, not recommended
        # Verify next safe actions don't recommend activation
        for action in report["next_safe_actions"]:
            assert "activate" not in action.lower()


class TestDeterministicOutput:
    def test_deterministic(self):
        r1 = build_report(SAMPLE_QUEUE, SAMPLE_PREP, release_hold="HOLD")
        r2 = build_report(SAMPLE_QUEUE, SAMPLE_PREP, release_hold="HOLD")
        assert r1 == r2


class TestReleaseHoldMismatch:
    def test_mismatch_fails(self):
        with pytest.raises(ValueError, match="release_hold"):
            build_report(SAMPLE_QUEUE, SAMPLE_PREP, release_hold="NOT_HOLD")


class TestWriteOutputs:
    def test_write_json(self):
        report = build_report(SAMPLE_QUEUE, SAMPLE_PREP, release_hold="HOLD")
        with tempfile.TemporaryDirectory() as tmpdir:
            out = pathlib.Path(tmpdir) / "report.json"
            write_json(report, out)
            assert out.exists()
            data = json.loads(out.read_text())
            assert data["frozen_file_count"] == 3

    def test_write_manifest(self):
        report = build_report(SAMPLE_QUEUE, SAMPLE_PREP, release_hold="HOLD")
        with tempfile.TemporaryDirectory() as tmpdir:
            out = pathlib.Path(tmpdir) / "manifest.json"
            write_manifest(report, out)
            data = json.loads(out.read_text())
            assert data["release_hold"] == "HOLD"

    def test_write_html(self):
        report = build_report(SAMPLE_QUEUE, SAMPLE_PREP, release_hold="HOLD")
        html = render_html(report)
        with tempfile.TemporaryDirectory() as tmpdir:
            out = pathlib.Path(tmpdir) / "report.html"
            write_html(html, out)
            assert out.exists()
            content = out.read_text()
            assert "<!DOCTYPE html>" in content
