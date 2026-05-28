"""Tests for frozen_backup_manifest.py — T15501."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.frozen_backup_manifest import (
    BACKUP_CLASSES,
    FORBIDDEN_BACKUP_STATUSES,
    FORBIDDEN_FINAL_STATUSES,
    RELEASE_HOLD_REQUIRED,
    BackupManifestItem,
    build_backup_manifest,
    build_manifest_item,
    compute_manifest_hash,
    render_manifest_markdown,
)

FIXTURE_DIR = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "frozen_backup_manifest"


@pytest.fixture
def sample_prep():
    return json.loads((FIXTURE_DIR / "sample_decision_prep.json").read_text())


@pytest.fixture
def sample_inventory():
    return [
        {
            "path": "core/live_runner.py",
            "exists": True,
            "sha256": "5fe494dad7f7d379ece5c6966530f4d220df94d40ceeec820521df8a22519831",
            "size_bytes": 4202,
            "line_count": 107,
        },
        {
            "path": "scripts/live_playbook.py",
            "exists": True,
            "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "size_bytes": 3500,
            "line_count": 80,
        },
        {
            "path": "scripts/run_shadow_universe_collector.py",
            "exists": True,
            "sha256": "1111111111111111111111111111111111111111111111111111111111111111",
            "size_bytes": 2100,
            "line_count": 50,
        },
    ]


class TestBackupRequiredForActions:
    def test_archive_requires_backup(self, sample_prep, sample_inventory):
        items = build_backup_manifest(sample_prep, sample_inventory)
        archive_item = next(i for i in items if i.candidate_action == "PREPARE_ARCHIVE_AFTER_BACKUP")
        assert archive_item.backup_required is True
        assert archive_item.backup_class == "REQUIRED_BEFORE_ARCHIVE"

    def test_delete_requires_backup(self, sample_prep, sample_inventory):
        # Modify fixture to have delete
        prep = [{**sample_prep[0], "candidate_action": "PREPARE_DELETE_AFTER_BACKUP", "current_disposition": "CANDIDATE_FOR_DELETE"}]
        items = build_backup_manifest(prep, sample_inventory)
        assert items[0].backup_required is True
        assert items[0].backup_class == "REQUIRED_BEFORE_DELETE"

    def test_rewrite_requires_backup(self, sample_prep, sample_inventory):
        items = build_backup_manifest(sample_prep, sample_inventory)
        rewrite_item = next(i for i in items if i.candidate_action == "PREPARE_OFFLINE_REWRITE")
        assert rewrite_item.backup_required is True
        assert rewrite_item.backup_class == "REQUIRED_BEFORE_REWRITE"


class TestKeepFrozenOptional:
    def test_keep_frozen_optional_backup(self, sample_prep, sample_inventory):
        items = build_backup_manifest(sample_prep, sample_inventory)
        frozen_item = next(i for i in items if i.candidate_action == "KEEP_FROZEN")
        assert frozen_item.backup_required is False
        assert frozen_item.backup_class == "OPTIONAL_FOR_KEEP_FROZEN"


class TestUnknownRequiresReview:
    def test_unknown_class(self):
        prep = [{"path": "unknown.py", "candidate_action": "UNKNOWN_ACTION", "priority": "UNKNOWN"}]
        items = build_backup_manifest(prep, [])
        assert items[0].backup_class == "UNKNOWN"


class TestNoForbiddenStatuses:
    def test_no_backup_done(self, sample_prep, sample_inventory):
        items = build_backup_manifest(sample_prep, sample_inventory)
        for item in items:
            assert item.current_status != "BACKUP_DONE"
            assert item.current_status not in FORBIDDEN_BACKUP_STATUSES
            assert item.current_status not in FORBIDDEN_FINAL_STATUSES

    def test_no_safe_to_delete(self, sample_prep, sample_inventory):
        items = build_backup_manifest(sample_prep, sample_inventory)
        for item in items:
            assert item.current_status != "SAFE_TO_DELETE"

    def test_no_safe_to_move(self, sample_prep, sample_inventory):
        items = build_backup_manifest(sample_prep, sample_inventory)
        for item in items:
            assert item.current_status != "SAFE_TO_MOVE"

    def test_no_safe_to_execute(self, sample_prep, sample_inventory):
        items = build_backup_manifest(sample_prep, sample_inventory)
        for item in items:
            assert item.current_status != "SAFE_TO_EXECUTE"


class TestProposedPathsHypothetical:
    def test_paths_start_with_archive_simulation(self, sample_prep, sample_inventory):
        items = build_backup_manifest(sample_prep, sample_inventory)
        for item in items:
            assert item.proposed_backup_path.startswith("archive_simulation/")
            assert item.proposed_backup_manifest_path.startswith("archive_simulation/")


class TestReleaseHoldMismatch:
    def test_release_hold_mismatch_fails(self, sample_prep, sample_inventory):
        with pytest.raises(ValueError, match="release_hold"):
            build_backup_manifest(sample_prep, sample_inventory, release_hold="RELEASED")


class TestDeterministic:
    def test_deterministic_output(self, sample_prep, sample_inventory):
        items1 = build_backup_manifest(sample_prep, sample_inventory)
        items2 = build_backup_manifest(sample_prep, sample_inventory)
        h1 = compute_manifest_hash(items1)
        h2 = compute_manifest_hash(items2)
        assert h1 == h2


class TestFrozenFilesNotTouched:
    def test_no_touch_required(self, sample_prep, sample_inventory):
        items = build_backup_manifest(sample_prep, sample_inventory)
        for item in items:
            assert item.no_touch_required is True
            assert item.no_execution is True
            assert item.no_import is True
            assert item.no_stage is True
            assert item.backup_allowed_now is False


class TestSafetyFlags:
    def test_all_items_hold_and_advisory(self, sample_prep, sample_inventory):
        items = build_backup_manifest(sample_prep, sample_inventory)
        for item in items:
            assert item.release_hold == "HOLD"
            assert item.advisory_only is True
            assert item.human_review_required is True
            assert item.required_human_approval is True
            assert item.backup_simulation_only is True


class TestRenderMarkdown:
    def test_markdown_contains_safety_boundary(self, sample_prep, sample_inventory):
        items = build_backup_manifest(sample_prep, sample_inventory)
        md = render_manifest_markdown(items)
        assert "Safety Boundary" in md
        assert "backup_allowed_now" in md
        assert "simulation_only" in md


class TestInventoryIntegration:
    def test_inventory_metadata_used(self, sample_prep, sample_inventory):
        items = build_backup_manifest(sample_prep, sample_inventory)
        live = next(i for i in items if i.path == "core/live_runner.py")
        assert live.exists is True
        assert live.size_bytes == 4202
        assert live.sha256 == "5fe494dad7f7d379ece5c6966530f4d220df94d40ceeec820521df8a22519831"
