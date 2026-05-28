"""Tests for frozen_archive_simulation.py — T15501."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.frozen_archive_simulation import (
    FORBIDDEN_FINAL_STATUSES,
    VALID_FINAL_STATUSES,
    ArchiveSimulationItem,
    build_archive_simulation,
    build_simulation_item,
    compute_simulation_hash,
    render_simulation_markdown,
)

FIXTURE_DIR = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "frozen_archive_simulation"


@pytest.fixture
def sample_backup_manifest():
    return json.loads((FIXTURE_DIR / "sample_backup_manifest.json").read_text())


class TestSimulationOnly:
    def test_would_copy_false(self, sample_backup_manifest):
        items = build_archive_simulation(sample_backup_manifest)
        for item in items:
            assert item.would_copy is False

    def test_would_move_false(self, sample_backup_manifest):
        items = build_archive_simulation(sample_backup_manifest)
        for item in items:
            assert item.would_move is False

    def test_would_delete_false(self, sample_backup_manifest):
        items = build_archive_simulation(sample_backup_manifest)
        for item in items:
            assert item.would_delete is False

    def test_would_modify_false(self, sample_backup_manifest):
        items = build_archive_simulation(sample_backup_manifest)
        for item in items:
            assert item.would_modify is False

    def test_simulation_only_true(self, sample_backup_manifest):
        items = build_archive_simulation(sample_backup_manifest)
        for item in items:
            assert item.simulation_only is True


class TestForbiddenFinalStatuses:
    def test_no_archived_status(self, sample_backup_manifest):
        items = build_archive_simulation(sample_backup_manifest)
        for item in items:
            assert item.final_status != "ARCHIVED"

    def test_no_deleted_status(self, sample_backup_manifest):
        items = build_archive_simulation(sample_backup_manifest)
        for item in items:
            assert item.final_status != "DELETED"

    def test_no_moved_status(self, sample_backup_manifest):
        items = build_archive_simulation(sample_backup_manifest)
        for item in items:
            assert item.final_status != "MOVED"

    def test_no_executed_status(self, sample_backup_manifest):
        items = build_archive_simulation(sample_backup_manifest)
        for item in items:
            assert item.final_status != "EXECUTED"

    def test_no_imported_status(self, sample_backup_manifest):
        items = build_archive_simulation(sample_backup_manifest)
        for item in items:
            assert item.final_status != "IMPORTED"

    def test_no_activated_status(self, sample_backup_manifest):
        items = build_archive_simulation(sample_backup_manifest)
        for item in items:
            assert item.final_status != "ACTIVATED"

    def test_all_statuses_valid(self, sample_backup_manifest):
        items = build_archive_simulation(sample_backup_manifest)
        for item in items:
            assert item.final_status in VALID_FINAL_STATUSES


class TestArchivePathsHypothetical:
    def test_simulated_archive_paths(self, sample_backup_manifest):
        items = build_archive_simulation(sample_backup_manifest)
        for item in items:
            assert item.simulated_archive_path.startswith("archive_simulation/")
            assert item.simulated_backup_path.startswith("archive_simulation/")


class TestHumanApprovalRequired:
    def test_human_approval_required(self, sample_backup_manifest):
        items = build_archive_simulation(sample_backup_manifest)
        for item in items:
            assert item.human_approval_required is True


class TestBackupRequiredWhereApplicable:
    def test_backup_required_for_archive(self, sample_backup_manifest):
        items = build_archive_simulation(sample_backup_manifest)
        archive_items = [
            i for i in items if i.proposed_action in (
                "PREPARE_ARCHIVE_AFTER_BACKUP",
                "PREPARE_DELETE_AFTER_BACKUP",
                "PREPARE_OFFLINE_REWRITE",
            )
        ]
        for item in archive_items:
            assert item.backup_required is True

    def test_backup_not_required_for_keep_frozen(self, sample_backup_manifest):
        items = build_archive_simulation(sample_backup_manifest)
        frozen_items = [i for i in items if i.proposed_action == "KEEP_FROZEN"]
        for item in frozen_items:
            assert item.backup_required is False


class TestReleaseHoldMismatch:
    def test_release_hold_mismatch_fails(self, sample_backup_manifest):
        with pytest.raises(ValueError, match="release_hold"):
            build_archive_simulation(sample_backup_manifest, release_hold="RELEASED")


class TestDeterministic:
    def test_deterministic_output(self, sample_backup_manifest):
        items1 = build_archive_simulation(sample_backup_manifest)
        items2 = build_archive_simulation(sample_backup_manifest)
        h1 = compute_simulation_hash(items1)
        h2 = compute_simulation_hash(items2)
        assert h1 == h2


class TestNoActualFileOperations:
    def test_no_actual_operations(self, sample_backup_manifest):
        items = build_archive_simulation(sample_backup_manifest)
        for item in items:
            assert item.would_copy is False
            assert item.would_move is False
            assert item.would_delete is False
            assert item.would_modify is False
            assert item.simulation_only is True


class TestStatusMapping:
    def test_keep_frozen_no_action(self):
        item = build_simulation_item({
            "path": "test.py",
            "candidate_action": "KEEP_FROZEN",
            "backup_required": False,
            "proposed_backup_path": "archive_simulation/frozen_files/test_py",
            "rollback_reference": "rollback_sim_test_py",
        })
        assert item.final_status == "KEEP_FROZEN_NO_ACTION"

    def test_needs_more_review(self):
        item = build_simulation_item({
            "path": "test.py",
            "candidate_action": "NEEDS_MORE_REVIEW",
            "backup_class": "REVIEW_REQUIRED",
            "backup_required": False,
            "proposed_backup_path": "archive_simulation/frozen_files/test_py",
            "rollback_reference": "rollback_sim_test_py",
        })
        assert item.final_status == "REVIEW_REQUIRED"

    def test_unknown_blocked(self):
        item = build_simulation_item({
            "path": "test.py",
            "candidate_action": "UNKNOWN",
            "backup_class": "UNKNOWN",
            "backup_required": False,
            "proposed_backup_path": "archive_simulation/frozen_files/test_py",
            "rollback_reference": "rollback_sim_test_py",
        })
        assert item.final_status == "BLOCKED_UNKNOWN_RISK"

    def test_blocked_pending_backup(self):
        item = build_simulation_item({
            "path": "test.py",
            "candidate_action": "PREPARE_ARCHIVE_AFTER_BACKUP",
            "backup_class": "REQUIRED_BEFORE_ARCHIVE",
            "backup_required": True,
            "proposed_backup_path": "archive_simulation/frozen_files/test_py",
            "rollback_reference": "rollback_sim_test_py",
        })
        assert item.final_status == "BLOCKED_PENDING_BACKUP"


class TestRenderMarkdown:
    def test_markdown_contains_safety(self, sample_backup_manifest):
        items = build_archive_simulation(sample_backup_manifest)
        md = render_simulation_markdown(items)
        assert "would_copy" in md
        assert "simulation_only" in md
