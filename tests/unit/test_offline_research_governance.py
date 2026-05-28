"""Tests for offline research governance validator.

No network. No exchange. No runtime. No planner. Advisory only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.offline_research_governance import (
    REQUIRED_CHECKLISTS,
    REQUIRED_OPERATOR_MANUALS,
    REQUIRED_RECOVERY_DOCS,
    REQUIRED_RUNBOOKS,
    SAFETY_KEYWORDS,
    check_file_contains,
    check_file_exists,
    run_full_governance_validation,
    validate_no_forbidden_approvals,
    validate_required_docs,
    validate_safety_statements,
    validate_untracked_warning,
)


DOCS_ROOT = Path(__file__).resolve().parent.parent.parent / "docs"


class TestCheckFileExists:
    def test_existing_file(self):
        # Use a file we know exists
        assert check_file_exists(DOCS_ROOT, "ARCHITECTURE.md") is True

    def test_missing_file(self):
        assert check_file_exists(DOCS_ROOT, "nonexistent_file_12345.md") is False


class TestCheckFileContains:
    def test_keyword_found(self, tmp_path):
        p = tmp_path / "test.md"
        p.write_text("release_hold is HOLD and advisory_only")
        result = check_file_contains(p, ["release_hold", "HOLD"])
        assert result["release_hold"] is True
        assert result["HOLD"] is True

    def test_keyword_not_found(self, tmp_path):
        p = tmp_path / "test.md"
        p.write_text("nothing relevant here")
        result = check_file_contains(p, ["release_hold"])
        assert result["release_hold"] is False

    def test_missing_file(self, tmp_path):
        result = check_file_contains(tmp_path / "nope.md", ["test"])
        assert result["test"] is False


class TestValidateRequiredDocs:
    def test_returns_structured_result(self):
        result = validate_required_docs(DOCS_ROOT)
        assert "valid" in result
        assert "found" in result
        assert "missing" in result
        assert "total_required" in result

    def test_total_required_count(self):
        result = validate_required_docs(DOCS_ROOT)
        expected = len(REQUIRED_OPERATOR_MANUALS) + len(REQUIRED_RUNBOOKS) + len(REQUIRED_CHECKLISTS) + len(REQUIRED_RECOVERY_DOCS)
        assert result["total_required"] == expected


class TestFullGovernanceValidation:
    def test_release_hold_mismatch(self):
        result = run_full_governance_validation(DOCS_ROOT, release_hold="RELEASE")
        assert result["valid"] is False
        assert any("release_hold" in e for e in result["errors"])

    def test_returns_structured_result(self):
        result = run_full_governance_validation(DOCS_ROOT, release_hold="HOLD")
        assert "valid" in result
        assert "errors" in result
        assert "doc_check" in result
        assert "safety_check" in result
        assert "approval_check" in result
        assert "untracked_warning_check" in result

    def test_release_hold_value_preserved(self):
        result = run_full_governance_validation(DOCS_ROOT, release_hold="HOLD")
        assert result["release_hold"] == "HOLD"
