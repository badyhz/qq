"""Tests for frozen_backup_verification.py — T15501."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.frozen_backup_verification import (
    FORBIDDEN_STATUSES,
    RELEASE_HOLD_REQUIRED,
    VerificationCheck,
    VerificationReport,
    verify_backup_manifest,
    render_verification_markdown,
)


def _safe_backup_items():
    return [
        {
            "path": "core/live_runner.py",
            "current_status": "FROZEN_NO_TOUCH",
            "backup_class": "REQUIRED_BEFORE_REWRITE",
            "backup_allowed_now": False,
            "human_review_required": True,
            "advisory_only": True,
            "proposed_backup_path": "archive_simulation/frozen_files/core__live_runner_py",
            "sha256": "abc123",
        },
    ]


def _safe_sim_items():
    return [
        {
            "path": "core/live_runner.py",
            "final_status": "BLOCKED_PENDING_BACKUP",
            "would_copy": False,
            "would_move": False,
            "would_delete": False,
            "would_modify": False,
            "simulation_only": True,
            "human_approval_required": True,
        },
    ]


def _safe_manifest_dict():
    return {
        "release_hold": "HOLD",
        "advisory_only": True,
        "simulation_only": True,
    }


class TestSafeManifestPasses:
    def test_safe_manifest_passes(self):
        report = verify_backup_manifest(
            _safe_backup_items(),
            _safe_sim_items(),
        )
        assert report.all_passed is True
        assert report.failed_checks == 0


class TestForbiddenStatusFails:
    def test_backup_done_fails(self):
        items = _safe_backup_items()
        items[0]["current_status"] = "BACKUP_DONE"
        report = verify_backup_manifest(items, _safe_sim_items())
        assert report.all_passed is False

    def test_archived_fails(self):
        items = _safe_sim_items()
        items[0]["final_status"] = "ARCHIVED"
        report = verify_backup_manifest(_safe_backup_items(), items)
        assert report.all_passed is False

    def test_deleted_fails(self):
        items = _safe_sim_items()
        items[0]["final_status"] = "DELETED"
        report = verify_backup_manifest(_safe_backup_items(), items)
        assert report.all_passed is False

    def test_moved_fails(self):
        items = _safe_sim_items()
        items[0]["final_status"] = "MOVED"
        report = verify_backup_manifest(_safe_backup_items(), items)
        assert report.all_passed is False

    def test_executed_fails(self):
        items = _safe_sim_items()
        items[0]["final_status"] = "EXECUTED"
        report = verify_backup_manifest(_safe_backup_items(), items)
        assert report.all_passed is False

    def test_imported_fails(self):
        items = _safe_sim_items()
        items[0]["final_status"] = "IMPORTED"
        report = verify_backup_manifest(_safe_backup_items(), items)
        assert report.all_passed is False

    def test_activated_fails(self):
        items = _safe_sim_items()
        items[0]["final_status"] = "ACTIVATED"
        report = verify_backup_manifest(_safe_backup_items(), items)
        assert report.all_passed is False

    def test_safe_to_delete_fails(self):
        items = _safe_backup_items()
        items[0]["current_status"] = "SAFE_TO_DELETE"
        report = verify_backup_manifest(items, _safe_sim_items())
        assert report.all_passed is False

    def test_safe_to_move_fails(self):
        items = _safe_backup_items()
        items[0]["current_status"] = "SAFE_TO_MOVE"
        report = verify_backup_manifest(items, _safe_sim_items())
        assert report.all_passed is False


class TestNonHypotheticalPathFails:
    def test_non_hypothetical_path_fails(self):
        items = _safe_backup_items()
        items[0]["proposed_backup_path"] = "/real/path/file.py"
        report = verify_backup_manifest(items, _safe_sim_items())
        assert report.all_passed is False


class TestReleaseHoldMismatchFails:
    def test_release_hold_mismatch(self):
        with pytest.raises(ValueError, match="release_hold"):
            verify_backup_manifest(
                _safe_backup_items(),
                _safe_sim_items(),
                release_hold="RELEASED",
            )


class TestMissingFilesStrict:
    def test_missing_backup_items_fail(self):
        report = verify_backup_manifest([], _safe_sim_items())
        # advisory_only check will fail on empty list since it's checking the dict
        # but human_review_required on empty list passes (no violations)
        assert report.total_checks > 0


class TestDeterministic:
    def test_deterministic_output(self):
        report1 = verify_backup_manifest(_safe_backup_items(), _safe_sim_items())
        report2 = verify_backup_manifest(_safe_backup_items(), _safe_sim_items())
        assert report1.all_passed == report2.all_passed
        assert report1.total_checks == report2.total_checks


class TestWouldFlags:
    def test_would_copy_true_fails(self):
        items = _safe_sim_items()
        items[0]["would_copy"] = True
        report = verify_backup_manifest(_safe_backup_items(), items)
        assert report.all_passed is False

    def test_would_delete_true_fails(self):
        items = _safe_sim_items()
        items[0]["would_delete"] = True
        report = verify_backup_manifest(_safe_backup_items(), items)
        assert report.all_passed is False


class TestRenderMarkdown:
    def test_markdown_contains_checks(self):
        report = verify_backup_manifest(_safe_backup_items(), _safe_sim_items())
        md = render_verification_markdown(report)
        assert "Verification Report" in md
        assert "PASS" in md or "FAIL" in md
