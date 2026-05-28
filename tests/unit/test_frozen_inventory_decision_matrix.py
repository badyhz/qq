"""Tests for frozen inventory human decision matrix.

Verifies:
- category mapping works
- high-risk submit/cancel/flatten never safe
- UNKNOWN requires human review
- release_hold != HOLD fails
- output deterministic
- no execution/import/stage flags true
- no approved/live/testnet activation text
- no forbidden markers
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.frozen_inventory_decision_matrix import (
    RELEASE_HOLD_REQUIRED,
    DecisionEntry,
    DecisionMatrix,
    build_decision_matrix,
    validate_no_forbidden_markers,
    validate_release_hold,
    write_json,
    write_manifest,
    write_markdown,
    _compute_risk_score,
    _determine_disposition,
)

FIXTURE_DIR = pathlib.Path(__file__).parent.parent / "fixtures" / "frozen_inventory_decision_matrix"
SAMPLE_INVENTORY = FIXTURE_DIR / "sample_inventory.json"


def _load_sample() -> dict:
    return json.loads(SAMPLE_INVENTORY.read_text(encoding="utf-8"))


def _build_sample_matrix() -> DecisionMatrix:
    return build_decision_matrix(_load_sample())


# ---------------------------------------------------------------------------
# Tests: category mapping
# ---------------------------------------------------------------------------

class TestCategoryMapping:
    def test_live_mapped(self):
        matrix = _build_sample_matrix()
        live = [e for e in matrix.entries if e.path == "scripts/live_playbook.py"]
        assert len(live) == 1
        assert live[0].category == "LIVE"

    def test_testnet_mapped(self):
        matrix = _build_sample_matrix()
        entry = [e for e in matrix.entries if "testnet" in e.path][0]
        assert entry.category == "TESTNET"

    def test_submit_mapped(self):
        matrix = _build_sample_matrix()
        entry = [e for e in matrix.entries if "submit" in e.path][0]
        assert entry.category == "SUBMIT"

    def test_flatten_mapped(self):
        matrix = _build_sample_matrix()
        entry = [e for e in matrix.entries if "flatten" in e.path][0]
        assert entry.category == "FLATTEN"

    def test_shadow_mapped(self):
        matrix = _build_sample_matrix()
        entry = [e for e in matrix.entries if "shadow" in e.path][0]
        assert entry.category == "SHADOW"


# ---------------------------------------------------------------------------
# Tests: high-risk never safe
# ---------------------------------------------------------------------------

class TestHighRiskNeverSafe:
    def test_submit_not_approved(self):
        matrix = _build_sample_matrix()
        entry = [e for e in matrix.entries if "submit" in e.path][0]
        assert entry.disposition not in ("APPROVED", "SAFE_TO_EXECUTE", "SAFE_TO_IMPORT")

    def test_flatten_not_approved(self):
        matrix = _build_sample_matrix()
        entry = [e for e in matrix.entries if "flatten" in e.path][0]
        assert entry.disposition not in ("APPROVED", "SAFE_TO_EXECUTE", "SAFE_TO_IMPORT")

    def test_cancel_keywords_force_rewrite_or_archive(self):
        kws = ["cancel"]
        disp, _ = _determine_disposition(kws, "CANCEL", 20)
        assert disp in ("CANDIDATE_FOR_REWRITE", "CANDIDATE_FOR_ARCHIVE")

    def test_flatten_keywords_force_rewrite(self):
        kws = ["flatten"]
        disp, _ = _determine_disposition(kws, "FLATTEN", 20)
        assert disp == "CANDIDATE_FOR_REWRITE"

    def test_submit_keywords_force_archive(self):
        kws = ["submit"]
        disp, _ = _determine_disposition(kws, "SUBMIT", 15)
        assert disp == "CANDIDATE_FOR_ARCHIVE"

    def test_live_never_approved(self):
        matrix = _build_sample_matrix()
        for entry in matrix.entries:
            if "live" in entry.risk_keywords:
                assert entry.disposition != "APPROVED"


# ---------------------------------------------------------------------------
# Tests: UNKNOWN requires human review
# ---------------------------------------------------------------------------

class TestUnknownRequiresHumanReview:
    def test_unknown_category_needs_review(self):
        disp, reason = _determine_disposition([], "UNKNOWN", 0)
        assert disp == "NEEDS_HUMAN_REVIEW"

    def test_unknown_in_matrix(self):
        matrix = _build_sample_matrix()
        unknowns = [e for e in matrix.entries if e.category == "UNKNOWN" and e.exists]
        for e in unknowns:
            assert e.disposition == "NEEDS_HUMAN_REVIEW"


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
# Tests: output deterministic
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_json_deterministic(self, tmp_path):
        matrix = _build_sample_matrix()
        p1 = tmp_path / "out1.json"
        p2 = tmp_path / "out2.json"
        write_json(matrix, p1)
        write_json(matrix, p2)
        assert p1.read_text() == p2.read_text()

    def test_markdown_deterministic(self, tmp_path):
        matrix = _build_sample_matrix()
        p1 = tmp_path / "out1.md"
        p2 = tmp_path / "out2.md"
        write_markdown(matrix, p1)
        write_markdown(matrix, p2)
        assert p1.read_text() == p2.read_text()

    def test_manifest_deterministic(self, tmp_path):
        matrix = _build_sample_matrix()
        p1 = tmp_path / "m1.json"
        p2 = tmp_path / "m2.json"
        write_manifest(matrix, p1)
        write_manifest(matrix, p2)
        assert p1.read_text() == p2.read_text()


# ---------------------------------------------------------------------------
# Tests: no execution/import/stage flags true
# ---------------------------------------------------------------------------

class TestSafetyFlags:
    def test_all_entries_no_execution(self):
        matrix = _build_sample_matrix()
        for entry in matrix.entries:
            assert entry.no_execution is True

    def test_all_entries_no_import(self):
        matrix = _build_sample_matrix()
        for entry in matrix.entries:
            assert entry.no_import is True

    def test_all_entries_no_stage(self):
        matrix = _build_sample_matrix()
        for entry in matrix.entries:
            assert entry.no_stage is True

    def test_all_entries_release_hold(self):
        matrix = _build_sample_matrix()
        for entry in matrix.entries:
            assert entry.release_hold == "HOLD"

    def test_all_entries_advisory_only(self):
        matrix = _build_sample_matrix()
        for entry in matrix.entries:
            assert entry.advisory_only is True

    def test_all_entries_human_review_required(self):
        matrix = _build_sample_matrix()
        for entry in matrix.entries:
            assert entry.human_review_required is True

    def test_manifest_safety_flags(self):
        matrix = _build_sample_matrix()
        m = matrix.manifest
        assert m["no_execution"] is True
        assert m["no_import"] is True
        assert m["no_stage"] is True
        assert m["no_approved"] is True
        assert m["no_safe_to_execute"] is True
        assert m["no_safe_to_import"] is True


# ---------------------------------------------------------------------------
# Tests: no approved/live/testnet activation text
# ---------------------------------------------------------------------------

class TestNoActivationText:
    def test_no_approved_in_disposition(self):
        matrix = _build_sample_matrix()
        for entry in matrix.entries:
            assert "APPROVED" not in entry.disposition.upper() or entry.disposition == "KEEP_FROZEN"

    def test_no_safe_to_execute(self):
        matrix = _build_sample_matrix()
        for entry in matrix.entries:
            assert "SAFE_TO_EXECUTE" not in entry.disposition

    def test_no_safe_to_import(self):
        matrix = _build_sample_matrix()
        for entry in matrix.entries:
            assert "SAFE_TO_IMPORT" not in entry.disposition

    def test_forbidden_markers_check(self):
        matrix = _build_sample_matrix()
        violations = validate_no_forbidden_markers(matrix)
        assert violations == []


# ---------------------------------------------------------------------------
# Tests: risk score
# ---------------------------------------------------------------------------

class TestRiskScore:
    def test_high_risk_keywords(self):
        score = _compute_risk_score(["flatten", "cancel", "submit"], "FLATTEN")
        assert score >= 30

    def test_no_keywords_zero(self):
        score = _compute_risk_score([], "UNKNOWN")
        assert score == 0

    def test_live_category_bonus(self):
        score = _compute_risk_score(["live"], "LIVE")
        assert score >= 25


# ---------------------------------------------------------------------------
# Tests: required fields in output
# ---------------------------------------------------------------------------

class TestRequiredFields:
    def test_entry_has_all_required_fields(self):
        matrix = _build_sample_matrix()
        required = [
            "path", "exists", "status", "category", "risk_keywords",
            "risk_score", "disposition", "disposition_reason",
            "required_human_action", "allowed_agent_action",
            "forbidden_agent_action", "no_execution", "no_import",
            "no_stage", "release_hold", "advisory_only", "human_review_required",
        ]
        for entry in matrix.entries:
            d = {f: getattr(entry, f) for f in required}
            for f in required:
                assert f in d, f"Missing field {f} in entry {entry.path}"

    def test_json_output_has_all_fields(self, tmp_path):
        matrix = _build_sample_matrix()
        out = tmp_path / "dm.json"
        write_json(matrix, out)
        data = json.loads(out.read_text())
        assert "manifest" in data
        assert "entries" in data
        for entry in data["entries"]:
            assert "disposition" in entry
            assert "no_execution" in entry
