"""Tests for frozen_backup_evidence_checklist.py — T16001."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.frozen_backup_evidence_checklist import (
    BLOCKER_STATUSES,
    FORBIDDEN_CHECKLIST_STATUSES,
    RELEASE_HOLD_REQUIRED,
    REQUIRED_EVIDENCE_FIELDS,
    EvidenceChecklistItem,
    build_checklist_item,
    build_evidence_checklist,
    compute_checklist_hash,
)


@pytest.fixture
def sample_manifest_items():
    return [
        {
            "path": "core/live_runner.py",
            "exists": True,
            "file_type": "python",
            "size_bytes": 4202,
            "sha256": "5fe494dad7f7d379ece5c6966530f4d220df94d40ceeec820521df8a22519831",
            "candidate_action": "PREPARE_OFFLINE_REWRITE",
            "priority": "P0_CRITICAL_REVIEW",
            "backup_class": "REQUIRED_BEFORE_REWRITE",
            "proposed_backup_path": "archive_simulation/frozen_files/core__live_runner_py",
            "rollback_reference": "rollback_sim_core__live_runner_py",
            "required_backup_evidence": ["sha256_hash_of_file"],
        },
        {
            "path": "scripts/live_playbook.py",
            "exists": True,
            "file_type": "python",
            "size_bytes": 3500,
            "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "candidate_action": "PREPARE_ARCHIVE_AFTER_BACKUP",
            "priority": "P1_HIGH",
            "backup_class": "REQUIRED_BEFORE_ARCHIVE",
            "proposed_backup_path": "archive_simulation/frozen_files/scripts__live_playbook_py",
            "rollback_reference": "rollback_sim_scripts__live_playbook_py",
            "required_backup_evidence": ["sha256_hash_of_file"],
        },
        {
            "path": "scripts/run_shadow_universe_collector.py",
            "exists": True,
            "file_type": "python",
            "size_bytes": 2100,
            "sha256": "1111111111111111111111111111111111111111111111111111111111111111",
            "candidate_action": "KEEP_FROZEN",
            "priority": "P3_LOW",
            "backup_class": "OPTIONAL_FOR_KEEP_FROZEN",
            "proposed_backup_path": "archive_simulation/frozen_files/scripts__run_shadow_universe_collector_py",
            "rollback_reference": "rollback_sim_scripts__run_shadow_universe_collector_py",
            "required_backup_evidence": [],
        },
    ]


@pytest.fixture
def sample_sim_items():
    return [
        {
            "path": "core/live_runner.py",
            "proposed_action": "PREPARE_OFFLINE_REWRITE",
            "final_status": "BLOCKED_PENDING_BACKUP",
            "simulation_only": True,
        },
        {
            "path": "scripts/live_playbook.py",
            "proposed_action": "PREPARE_ARCHIVE_AFTER_BACKUP",
            "final_status": "BLOCKED_PENDING_BACKUP",
            "simulation_only": True,
        },
        {
            "path": "scripts/run_shadow_universe_collector.py",
            "proposed_action": "KEEP_FROZEN",
            "final_status": "NO_ACTION_SIMULATED",
            "simulation_only": True,
        },
    ]


class TestAllPendingOrBlocked:
    def test_all_items_pending(self, sample_manifest_items, sample_sim_items):
        items = build_evidence_checklist(sample_manifest_items, sample_sim_items)
        for item in items:
            assert item.evidence_status == "PENDING"

    def test_no_item_complete(self, sample_manifest_items, sample_sim_items):
        items = build_evidence_checklist(sample_manifest_items, sample_sim_items)
        for item in items:
            assert item.evidence_status != "COMPLETE"
            assert item.evidence_status not in FORBIDDEN_CHECKLIST_STATUSES


class TestNoForbiddenStatuses:
    def test_no_backup_done(self, sample_manifest_items, sample_sim_items):
        items = build_evidence_checklist(sample_manifest_items, sample_sim_items)
        for item in items:
            assert item.evidence_status != "BACKUP_DONE"

    def test_no_approved(self, sample_manifest_items, sample_sim_items):
        items = build_evidence_checklist(sample_manifest_items, sample_sim_items)
        for item in items:
            assert item.evidence_status != "APPROVED"

    def test_no_safe_to_delete(self, sample_manifest_items, sample_sim_items):
        items = build_evidence_checklist(sample_manifest_items, sample_sim_items)
        for item in items:
            assert item.evidence_status != "SAFE_TO_DELETE"


class TestEvidenceRequirementsPresent:
    def test_required_evidence_fields(self, sample_manifest_items, sample_sim_items):
        items = build_evidence_checklist(sample_manifest_items, sample_sim_items)
        for item in items:
            for field in REQUIRED_EVIDENCE_FIELDS:
                assert field in item.required_evidence, f"missing {field} in {item.path}"

    def test_hash_evidence_present(self, sample_manifest_items, sample_sim_items):
        items = build_evidence_checklist(sample_manifest_items, sample_sim_items)
        for item in items:
            assert len(item.required_hash_evidence) > 0

    def test_size_evidence_present(self, sample_manifest_items, sample_sim_items):
        items = build_evidence_checklist(sample_manifest_items, sample_sim_items)
        for item in items:
            assert len(item.required_size_evidence) > 0

    def test_path_evidence_present(self, sample_manifest_items, sample_sim_items):
        items = build_evidence_checklist(sample_manifest_items, sample_sim_items)
        for item in items:
            assert len(item.required_path_evidence) > 0


class TestBlockerStatuses:
    def test_blocker_status_valid(self, sample_manifest_items, sample_sim_items):
        items = build_evidence_checklist(sample_manifest_items, sample_sim_items)
        for item in items:
            assert item.blocker_status in BLOCKER_STATUSES

    def test_rewrite_blocked_pending_evidence(self, sample_manifest_items, sample_sim_items):
        items = build_evidence_checklist(sample_manifest_items, sample_sim_items)
        rewrite = next(i for i in items if i.candidate_action == "PREPARE_OFFLINE_REWRITE")
        assert rewrite.blocker_status == "BLOCKED_PENDING_EVIDENCE"

    def test_archive_blocked_pending_evidence(self, sample_manifest_items, sample_sim_items):
        items = build_evidence_checklist(sample_manifest_items, sample_sim_items)
        archive = next(i for i in items if i.candidate_action == "PREPARE_ARCHIVE_AFTER_BACKUP")
        assert archive.blocker_status == "BLOCKED_PENDING_EVIDENCE"

    def test_keep_frozen_blocked_pending_approval(self, sample_manifest_items, sample_sim_items):
        items = build_evidence_checklist(sample_manifest_items, sample_sim_items)
        frozen = next(i for i in items if i.candidate_action == "KEEP_FROZEN")
        assert frozen.blocker_status == "BLOCKED_PENDING_HUMAN_APPROVAL"


class TestReleaseHoldMismatch:
    def test_release_hold_mismatch_fails(self, sample_manifest_items, sample_sim_items):
        with pytest.raises(ValueError, match="release_hold"):
            build_evidence_checklist(sample_manifest_items, sample_sim_items, release_hold="RELEASED")


class TestDeterministic:
    def test_deterministic_output(self, sample_manifest_items, sample_sim_items):
        items1 = build_evidence_checklist(sample_manifest_items, sample_sim_items)
        items2 = build_evidence_checklist(sample_manifest_items, sample_sim_items)
        assert compute_checklist_hash(items1) == compute_checklist_hash(items2)


class TestFrozenFilesNotTouched:
    def test_no_touch_flags(self, sample_manifest_items, sample_sim_items):
        items = build_evidence_checklist(sample_manifest_items, sample_sim_items)
        for item in items:
            assert item.no_touch_required is True
            assert item.backup_not_performed is True
            assert item.archive_not_performed is True
            assert item.delete_not_performed is True
            assert item.copy_not_performed is True
            assert item.move_not_performed is True


class TestSafetyFlags:
    def test_all_items_hold_and_advisory(self, sample_manifest_items, sample_sim_items):
        items = build_evidence_checklist(sample_manifest_items, sample_sim_items)
        for item in items:
            assert item.release_hold == "HOLD"
            assert item.advisory_only is True
            assert item.human_review_required is True


class TestChecklistIdFormat:
    def test_checklist_id_not_empty(self, sample_manifest_items, sample_sim_items):
        items = build_evidence_checklist(sample_manifest_items, sample_sim_items)
        for item in items:
            assert item.checklist_id.startswith("checklist_")
            assert len(item.checklist_id) > 10


class TestEvidencePathsPlaceholder:
    def test_placeholders_present(self, sample_manifest_items, sample_sim_items):
        items = build_evidence_checklist(sample_manifest_items, sample_sim_items)
        for item in items:
            assert len(item.evidence_paths_placeholder) > 0
            for p in item.evidence_paths_placeholder:
                assert "evidence/" in p
