"""Tests for frozen inventory archive plan (no-touch migration design).

Verifies:
- no-touch plan only
- requires_backup true for delete/archive candidates
- requires_human_approval true for all risky files
- no proposed action equals EXECUTE or IMPORT
- release_hold != HOLD fails
- deterministic output
- no frozen files modified
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.frozen_inventory_archive_plan import (
    RELEASE_HOLD_REQUIRED,
    FORBIDDEN_ACTIONS,
    ArchivePlan,
    build_archive_plan,
    validate_no_forbidden_actions,
    validate_no_touch,
    validate_release_hold,
    write_json,
    write_manifest,
    write_markdown,
)

FIXTURE_DIR = pathlib.Path(__file__).parent.parent / "fixtures" / "frozen_inventory_archive_plan"
SAMPLE_MATRIX = FIXTURE_DIR / "sample_decision_matrix.json"


def _load_sample() -> dict:
    return json.loads(SAMPLE_MATRIX.read_text(encoding="utf-8"))


def _build_sample_plan() -> ArchivePlan:
    return build_archive_plan(_load_sample())


# ---------------------------------------------------------------------------
# Tests: no-touch plan only
# ---------------------------------------------------------------------------

class TestNoTouchPlan:
    def test_all_entries_no_touch(self):
        plan = _build_sample_plan()
        for entry in plan.entries:
            assert entry.no_touch_confirmed is True

    def test_manifest_no_touch(self):
        plan = _build_sample_plan()
        assert plan.manifest["no_touch_plan_only"] is True
        assert plan.manifest["no_actual_move"] is True
        assert plan.manifest["no_actual_delete"] is True
        assert plan.manifest["no_actual_rename"] is True
        assert plan.manifest["no_actual_modify"] is True

    def test_validate_no_touch(self):
        plan = _build_sample_plan()
        violations = validate_no_touch(plan)
        assert violations == []


# ---------------------------------------------------------------------------
# Tests: requires_backup true for delete/archive candidates
# ---------------------------------------------------------------------------

class TestRequiresBackup:
    def test_archive_requires_backup(self):
        plan = _build_sample_plan()
        for entry in plan.entries:
            if entry.current_disposition == "CANDIDATE_FOR_ARCHIVE":
                assert entry.requires_backup is True

    def test_rewrite_requires_backup(self):
        plan = _build_sample_plan()
        for entry in plan.entries:
            if entry.current_disposition == "CANDIDATE_FOR_REWRITE":
                assert entry.requires_backup is True

    def test_delete_requires_backup(self):
        plan = _build_sample_plan()
        for entry in plan.entries:
            if entry.current_disposition == "CANDIDATE_FOR_DELETION_AFTER_BACKUP":
                assert entry.requires_backup is True

    def test_keep_frozen_no_backup(self):
        plan = _build_sample_plan()
        for entry in plan.entries:
            if entry.current_disposition == "KEEP_FROZEN":
                assert entry.requires_backup is False


# ---------------------------------------------------------------------------
# Tests: requires_human_approval true for all risky files
# ---------------------------------------------------------------------------

class TestRequiresHumanApproval:
    def test_risky_files_need_approval(self):
        plan = _build_sample_plan()
        for entry in plan.entries:
            if entry.current_disposition != "KEEP_FROZEN":
                assert entry.requires_human_approval is True

    def test_keep_frozen_no_approval(self):
        plan = _build_sample_plan()
        for entry in plan.entries:
            if entry.current_disposition == "KEEP_FROZEN":
                assert entry.requires_human_approval is False


# ---------------------------------------------------------------------------
# Tests: no forbidden actions
# ---------------------------------------------------------------------------

class TestNoForbiddenActions:
    def test_no_execute_action(self):
        plan = _build_sample_plan()
        for entry in plan.entries:
            assert entry.proposed_future_action != "EXECUTE"

    def test_no_import_action(self):
        plan = _build_sample_plan()
        for entry in plan.entries:
            assert entry.proposed_future_action != "IMPORT"

    def test_validate_forbidden_actions(self):
        plan = _build_sample_plan()
        violations = validate_no_forbidden_actions(plan)
        assert violations == []

    def test_all_proposed_actions_valid(self):
        plan = _build_sample_plan()
        valid_actions = {"NO_ACTION", "AWAIT_HUMAN_DECISION", "MOVE_TO_ARCHIVE_AFTER_APPROVAL",
                         "REWRITE_FROM_SCRATCH_AFTER_APPROVAL", "BACKUP_THEN_DELETE_AFTER_APPROVAL"}
        for entry in plan.entries:
            assert entry.proposed_future_action in valid_actions


# ---------------------------------------------------------------------------
# Tests: release_hold != HOLD fails
# ---------------------------------------------------------------------------

class TestReleaseHold:
    def test_hold_accepted(self):
        assert validate_release_hold(None, "HOLD") is True

    def test_rejected_values(self):
        for val in ["RELEASED", "", "hold", "HOLD ", " HOLD"]:
            assert validate_release_hold(None, val) is False


# ---------------------------------------------------------------------------
# Tests: deterministic output
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_json_deterministic(self, tmp_path):
        plan = _build_sample_plan()
        p1 = tmp_path / "out1.json"
        p2 = tmp_path / "out2.json"
        write_json(plan, p1)
        write_json(plan, p2)
        assert p1.read_text() == p2.read_text()

    def test_markdown_deterministic(self, tmp_path):
        plan = _build_sample_plan()
        p1 = tmp_path / "out1.md"
        p2 = tmp_path / "out2.md"
        write_markdown(plan, p1)
        write_markdown(plan, p2)
        assert p1.read_text() == p2.read_text()

    def test_manifest_deterministic(self, tmp_path):
        plan = _build_sample_plan()
        p1 = tmp_path / "m1.json"
        p2 = tmp_path / "m2.json"
        write_manifest(plan, p1)
        write_manifest(plan, p2)
        assert p1.read_text() == p2.read_text()


# ---------------------------------------------------------------------------
# Tests: categorization
# ---------------------------------------------------------------------------

class TestCategorization:
    def test_keep_frozen_list(self):
        plan = _build_sample_plan()
        assert "docs/safe_doc.md" in plan.keep_frozen

    def test_human_review_queue(self):
        plan = _build_sample_plan()
        assert "scripts/live_playbook.py" in plan.human_review_queue

    def test_archive_candidates(self):
        plan = _build_sample_plan()
        assert "scripts/submit_approved_candidates.py" in plan.archive_candidates

    def test_rewrite_candidates(self):
        plan = _build_sample_plan()
        assert "scripts/safe_flatten_testnet_symbol.py" in plan.rewrite_candidates


# ---------------------------------------------------------------------------
# Tests: output structure
# ---------------------------------------------------------------------------

class TestOutputStructure:
    def test_json_has_all_sections(self, tmp_path):
        plan = _build_sample_plan()
        out = tmp_path / "plan.json"
        write_json(plan, out)
        data = json.loads(out.read_text())
        assert "manifest" in data
        assert "entries" in data
        assert "keep_frozen" in data
        assert "human_review_queue" in data
        assert "archive_candidates" in data
        assert "rewrite_candidates" in data
        assert "delete_after_backup_candidates" in data
        assert "unknown_review_required" in data

    def test_entry_has_all_fields(self, tmp_path):
        plan = _build_sample_plan()
        out = tmp_path / "plan.json"
        write_json(plan, out)
        data = json.loads(out.read_text())
        required = [
            "path", "current_disposition", "proposed_future_action",
            "requires_backup", "requires_human_approval",
            "required_preconditions", "forbidden_until_approved",
            "rollback_note", "no_touch_confirmed",
        ]
        for entry in data["entries"]:
            for f in required:
                assert f in entry, f"Missing field {f}"
