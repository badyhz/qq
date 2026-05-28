"""Tests for frozen_rollback_plan.py — T15501."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.frozen_rollback_plan import (
    RELEASE_HOLD_REQUIRED,
    RollbackPlanItem,
    build_rollback_item,
    build_rollback_plan,
    compute_rollback_hash,
    render_rollback_markdown,
)


@pytest.fixture
def sample_sim_items():
    return [
        {
            "path": "core/live_runner.py",
            "proposed_action": "PREPARE_OFFLINE_REWRITE",
            "simulated_archive_path": "archive_simulation/archived/core__live_runner_py",
            "simulated_backup_path": "archive_simulation/frozen_files/core__live_runner_py",
            "backup_required": True,
            "rollback_plan_id": "rollback_sim_core__live_runner_py",
        },
        {
            "path": "scripts/live_playbook.py",
            "proposed_action": "PREPARE_ARCHIVE_AFTER_BACKUP",
            "simulated_archive_path": "archive_simulation/archived/scripts__live_playbook_py",
            "simulated_backup_path": "archive_simulation/frozen_files/scripts__live_playbook_py",
            "backup_required": True,
            "rollback_plan_id": "rollback_sim_scripts__live_playbook_py",
        },
    ]


class TestRollbackRequiresBackupManifest:
    def test_required_backup_manifest_present(self, sample_sim_items):
        items = build_rollback_plan(sample_sim_items)
        for item in items:
            assert item.required_backup_manifest
            assert "frozen_backup_manifest" in item.required_backup_manifest


class TestRollbackRequiresHashCheck:
    def test_required_hash_check_present(self, sample_sim_items):
        items = build_rollback_plan(sample_sim_items)
        for item in items:
            assert item.required_hash_check
            assert "sha256" in item.required_hash_check


class TestAutomatedRestoreForbidden:
    def test_forbidden_automated_restore(self, sample_sim_items):
        items = build_rollback_plan(sample_sim_items)
        for item in items:
            assert item.forbidden_automated_restore is True


class TestReleaseHoldMismatch:
    def test_release_hold_mismatch_fails(self, sample_sim_items):
        with pytest.raises(ValueError, match="release_hold"):
            build_rollback_plan(sample_sim_items, release_hold="RELEASED")


class TestNoActualRestoreExecution:
    def test_no_execution(self, sample_sim_items):
        items = build_rollback_plan(sample_sim_items)
        for item in items:
            assert item.no_execution is True
            assert item.no_import is True

    def test_manual_restore_is_template(self, sample_sim_items):
        items = build_rollback_plan(sample_sim_items)
        for item in items:
            assert "MANUAL RESTORE TEMPLATE" in item.manual_restore_command_template
            assert "NOT executable" in item.manual_restore_command_template


class TestDeterministic:
    def test_deterministic_output(self, sample_sim_items):
        items1 = build_rollback_plan(sample_sim_items)
        items2 = build_rollback_plan(sample_sim_items)
        h1 = compute_rollback_hash(items1)
        h2 = compute_rollback_hash(items2)
        assert h1 == h2


class TestHumanApprovalRequired:
    def test_human_approval_required(self, sample_sim_items):
        items = build_rollback_plan(sample_sim_items)
        for item in items:
            assert item.human_approval_required is True


class TestRenderMarkdown:
    def test_markdown_contains_safety(self, sample_sim_items):
        items = build_rollback_plan(sample_sim_items)
        md = render_rollback_markdown(items)
        assert "forbidden_automated_restore" in md
        assert "MANUAL RESTORE TEMPLATE" in md


class TestItemStructure:
    def test_all_fields_present(self, sample_sim_items):
        items = build_rollback_plan(sample_sim_items)
        for item in items:
            d = item.to_dict()
            assert "rollback_plan_id" in d
            assert "original_path" in d
            assert "simulated_archive_path" in d
            assert "simulated_backup_path" in d
            assert "rollback_preconditions" in d
            assert "required_backup_manifest" in d
            assert "required_hash_check" in d
            assert "manual_restore_command_template" in d
            assert "verification_steps" in d
            assert "forbidden_automated_restore" in d
            assert "human_approval_required" in d
            assert "no_execution" in d
            assert "no_import" in d
            assert "release_hold" in d
            assert d["release_hold"] == "HOLD"
