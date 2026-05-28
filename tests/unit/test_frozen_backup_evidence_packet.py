"""Tests for frozen_backup_evidence_packet.py — T16001."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.frozen_backup_evidence_packet import (
    PACKET_SECTIONS,
    RELEASE_HOLD_REQUIRED,
    EvidencePacket,
    build_packet,
    render_packet_html,
    render_packet_markdown,
)


@pytest.fixture
def sample_checklist_items():
    return [
        {
            "path": "core/live_runner.py",
            "candidate_action": "PREPARE_OFFLINE_REWRITE",
            "evidence_status": "PENDING",
            "blocker_status": "BLOCKED_PENDING_EVIDENCE",
            "required_evidence": ["original_path_confirmed", "original_sha256_recorded"],
            "required_hash_evidence": ["original_sha256_recorded", "known_hash=abc123"],
            "required_size_evidence": ["original_size_recorded", "known_size=4202_bytes"],
            "required_path_evidence": ["original_path_confirmed"],
            "required_rollback_note": "rollback_plan=rollback_sim_core__live_runner_py",
        },
    ]


@pytest.fixture
def sample_approval_forms():
    return [
        {
            "path": "core/live_runner.py",
            "form_id": "approval_form_core__live_runner_py",
            "form_type": "OFFLINE_REWRITE_APPROVAL_FORM",
            "candidate_action": "PREPARE_OFFLINE_REWRITE",
            "human_decision_placeholder": "PENDING_HUMAN_DECISION",
            "approval_conditions": ["all_evidence_collected"],
        },
    ]


@pytest.fixture
def sample_validation_report():
    return {
        "all_passed": True,
        "total_checks": 6,
        "passed_checks": 6,
        "failed_checks": 0,
        "release_hold": "HOLD",
    }


@pytest.fixture
def sample_backup_manifest():
    return [
        {
            "path": "core/live_runner.py",
            "backup_class": "REQUIRED_BEFORE_REWRITE",
            "backup_required": True,
            "backup_allowed_now": False,
            "proposed_backup_path": "archive_simulation/frozen_files/core__live_runner_py",
            "required_backup_evidence": ["sha256_hash_of_file"],
        },
    ]


@pytest.fixture
def sample_archive_simulation():
    return [
        {
            "path": "core/live_runner.py",
            "proposed_action": "PREPARE_OFFLINE_REWRITE",
            "final_status": "BLOCKED_PENDING_BACKUP",
            "simulation_only": True,
        },
    ]


class TestAllSectionsPresent:
    def test_all_sections_in_packet(
        self, sample_checklist_items, sample_approval_forms,
        sample_validation_report, sample_backup_manifest, sample_archive_simulation,
    ):
        packet = build_packet(
            sample_checklist_items, sample_approval_forms,
            sample_validation_report, sample_backup_manifest,
            sample_archive_simulation,
        )
        for section in PACKET_SECTIONS:
            assert section in packet.sections, f"missing section: {section}"


class TestNoActivationRecommendation:
    def test_no_activation_in_next_actions(
        self, sample_checklist_items, sample_approval_forms,
        sample_validation_report, sample_backup_manifest, sample_archive_simulation,
    ):
        packet = build_packet(
            sample_checklist_items, sample_approval_forms,
            sample_validation_report, sample_backup_manifest,
            sample_archive_simulation,
        )
        next_actions = packet.sections.get("Next Safe Actions", {})
        steps = next_actions.get("steps", [])
        for step in steps:
            lower = step.lower()
            assert "activate live" not in lower
            assert "activate testnet" not in lower
            assert "enable runtime" not in lower


class TestNoImmediateDeleteMoveCopy:
    def test_forbidden_decisions_listed(
        self, sample_checklist_items, sample_approval_forms,
        sample_validation_report, sample_backup_manifest, sample_archive_simulation,
    ):
        packet = build_packet(
            sample_checklist_items, sample_approval_forms,
            sample_validation_report, sample_backup_manifest,
            sample_archive_simulation,
        )
        forbidden = packet.sections.get("Forbidden Decisions", [])
        assert "DELETE_NOW" in forbidden
        assert "MOVE_NOW" in forbidden
        assert "COPY_NOW" in forbidden
        assert "ARCHIVE_NOW" in forbidden


class TestReleaseHoldMismatch:
    def test_release_hold_mismatch_fails(
        self, sample_checklist_items, sample_approval_forms,
        sample_validation_report, sample_backup_manifest, sample_archive_simulation,
    ):
        with pytest.raises(ValueError, match="release_hold"):
            build_packet(
                sample_checklist_items, sample_approval_forms,
                sample_validation_report, sample_backup_manifest,
                sample_archive_simulation,
                release_hold="RELEASED",
            )


class TestDeterministic:
    def test_deterministic_output(
        self, sample_checklist_items, sample_approval_forms,
        sample_validation_report, sample_backup_manifest, sample_archive_simulation,
    ):
        p1 = build_packet(
            sample_checklist_items, sample_approval_forms,
            sample_validation_report, sample_backup_manifest,
            sample_archive_simulation,
        )
        p2 = build_packet(
            sample_checklist_items, sample_approval_forms,
            sample_validation_report, sample_backup_manifest,
            sample_archive_simulation,
        )
        h1 = hashlib.sha256(json.dumps(p1.to_dict(), sort_keys=True).encode()).hexdigest()
        h2 = hashlib.sha256(json.dumps(p2.to_dict(), sort_keys=True).encode()).hexdigest()
        assert h1 == h2


class TestHtmlOffline:
    def test_html_no_cdn(
        self, sample_checklist_items, sample_approval_forms,
        sample_validation_report, sample_backup_manifest, sample_archive_simulation,
    ):
        packet = build_packet(
            sample_checklist_items, sample_approval_forms,
            sample_validation_report, sample_backup_manifest,
            sample_archive_simulation,
        )
        html = render_packet_html(packet)
        assert "cdn" not in html.lower()
        assert "https://" not in html
        assert "<script src=" not in html

    def test_html_standalone(
        self, sample_checklist_items, sample_approval_forms,
        sample_validation_report, sample_backup_manifest, sample_archive_simulation,
    ):
        packet = build_packet(
            sample_checklist_items, sample_approval_forms,
            sample_validation_report, sample_backup_manifest,
            sample_archive_simulation,
        )
        html = render_packet_html(packet)
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html
        assert "<style>" in html


class TestSafetyBoundary:
    def test_safety_boundary_flags(
        self, sample_checklist_items, sample_approval_forms,
        sample_validation_report, sample_backup_manifest, sample_archive_simulation,
    ):
        packet = build_packet(
            sample_checklist_items, sample_approval_forms,
            sample_validation_report, sample_backup_manifest,
            sample_archive_simulation,
        )
        sb = packet.sections["Safety Boundary"]
        assert sb["no_actual_backup"] is True
        assert sb["no_actual_archive"] is True
        assert sb["no_actual_delete"] is True
        assert sb["release_hold"] == "HOLD"
        assert sb["advisory_only"] is True


import hashlib
