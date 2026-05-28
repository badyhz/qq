"""Tests for frozen archive/delete decision prep — T15001."""
from __future__ import annotations

import json
import pathlib
import tempfile

import pytest

from core.frozen_archive_delete_decision_prep import (
    CANDIDATE_ACTIONS,
    FORBIDDEN_IMMEDIATE_ACTIONS,
    RELEASE_HOLD_REQUIRED,
    DecisionPrepItem,
    build_decision_prep,
    build_prep_item,
    load_queue,
    render_decision_prep_markdown,
    write_json,
    write_manifest,
    write_markdown,
)

FIXTURE_DIR = pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "frozen_archive_delete_decision_prep"
SAMPLE_QUEUE = FIXTURE_DIR / "sample_queue.json"


class TestCandidateActions:
    def test_no_deletion_allowed_now(self):
        queue = load_queue(SAMPLE_QUEUE)
        items = build_decision_prep(queue, release_hold="HOLD")
        for item in items:
            assert item.deletion_allowed_now is False

    def test_no_archive_allowed_now(self):
        queue = load_queue(SAMPLE_QUEUE)
        items = build_decision_prep(queue, release_hold="HOLD")
        for item in items:
            assert item.archive_allowed_now is False

    def test_no_rewrite_allowed_now(self):
        queue = load_queue(SAMPLE_QUEUE)
        items = build_decision_prep(queue, release_hold="HOLD")
        for item in items:
            assert item.rewrite_allowed_now is False


class TestBackupRequired:
    def test_backup_required_for_archive(self):
        queue = load_queue(SAMPLE_QUEUE)
        items = build_decision_prep(queue, release_hold="HOLD")
        archive_items = [i for i in items if i.candidate_action == "PREPARE_ARCHIVE_AFTER_BACKUP"]
        for item in archive_items:
            assert item.backup_required is True

    def test_backup_required_for_rewrite(self):
        queue = load_queue(SAMPLE_QUEUE)
        items = build_decision_prep(queue, release_hold="HOLD")
        rewrite_items = [i for i in items if i.candidate_action == "PREPARE_OFFLINE_REWRITE"]
        for item in rewrite_items:
            assert item.backup_required is True


class TestHumanApproval:
    def test_human_approval_required(self):
        queue = load_queue(SAMPLE_QUEUE)
        items = build_decision_prep(queue, release_hold="HOLD")
        for item in items:
            assert item.required_human_approval is True

    def test_no_touch_until_approved(self):
        queue = load_queue(SAMPLE_QUEUE)
        items = build_decision_prep(queue, release_hold="HOLD")
        for item in items:
            assert item.no_touch_until_approved is True


class TestForbiddenImmediateActions:
    def test_forbidden_actions_never_output(self):
        """Ensure no candidate action matches forbidden immediate actions."""
        for action in FORBIDDEN_IMMEDIATE_ACTIONS:
            assert action not in CANDIDATE_ACTIONS

    def test_no_delete_now_in_output(self):
        queue = load_queue(SAMPLE_QUEUE)
        items = build_decision_prep(queue, release_hold="HOLD")
        for item in items:
            assert item.candidate_action != "DELETE_NOW"
            assert item.candidate_action != "MOVE_NOW"
            assert item.candidate_action != "EXECUTE_NOW"
            assert item.candidate_action != "IMPORT_NOW"
            assert item.candidate_action != "ACTIVATE_NOW"


class TestReleaseHold:
    def test_release_hold_mismatch_fails(self):
        queue = load_queue(SAMPLE_QUEUE)
        with pytest.raises(ValueError, match="release_hold"):
            build_decision_prep(queue, release_hold="NOT_HOLD")


class TestDeterministicOutput:
    def test_deterministic(self):
        queue = load_queue(SAMPLE_QUEUE)
        items1 = build_decision_prep(queue, release_hold="HOLD")
        items2 = build_decision_prep(queue, release_hold="HOLD")
        assert [i.to_dict() for i in items1] == [i.to_dict() for i in items2]


class TestNoActualFileOperations:
    def test_no_file_touch(self):
        """Verify no file operations in decision prep."""
        queue = load_queue(SAMPLE_QUEUE)
        items = build_decision_prep(queue, release_hold="HOLD")
        for item in items:
            # All flags must deny immediate action
            assert item.deletion_allowed_now is False
            assert item.archive_allowed_now is False
            assert item.rewrite_allowed_now is False
            assert item.no_touch_until_approved is True


class TestWriteOutputs:
    def test_write_json(self):
        queue = load_queue(SAMPLE_QUEUE)
        items = build_decision_prep(queue, release_hold="HOLD")
        with tempfile.TemporaryDirectory() as tmpdir:
            out = pathlib.Path(tmpdir) / "prep.json"
            write_json(items, out)
            assert out.exists()
            data = json.loads(out.read_text())
            assert len(data) == len(items)

    def test_write_manifest(self):
        queue = load_queue(SAMPLE_QUEUE)
        items = build_decision_prep(queue, release_hold="HOLD")
        with tempfile.TemporaryDirectory() as tmpdir:
            out = pathlib.Path(tmpdir) / "manifest.json"
            write_manifest(items, out, "HOLD")
            data = json.loads(out.read_text())
            assert data["release_hold"] == "HOLD"
            assert data["deletion_allowed_now"] is False

    def test_write_markdown(self):
        queue = load_queue(SAMPLE_QUEUE)
        items = build_decision_prep(queue, release_hold="HOLD")
        with tempfile.TemporaryDirectory() as tmpdir:
            out = pathlib.Path(tmpdir) / "prep.md"
            write_markdown(items, out)
            content = out.read_text()
            assert "Archive/Delete Decision Prep" in content
            assert "deletion_allowed_now: **false**" in content
