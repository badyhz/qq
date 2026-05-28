"""Tests for offline research recovery documentation.

No network. No exchange. No runtime. No planner. Advisory only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

RECOVERY_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "recovery"

REQUIRED_RECOVERY_DOCS = [
    "missing_quality_artifacts_recovery.md",
    "corrupted_json_recovery.md",
    "reproducibility_mismatch_recovery.md",
    "invalid_safety_flags_recovery.md",
    "missing_review_packet_recovery.md",
    "failed_full_suite_recovery.md",
    "untracked_external_state_recovery.md",
    "bad_commit_recovery.md",
    "restore_to_tags_recovery.md",
]

REQUIRED_SECTIONS = [
    "symptom",
    "cause",
    "inspect",
    "recover",
    "forbidden",
    "escalation",
    "verification",
]


class TestRecoveryDocsExist:
    @pytest.mark.parametrize("doc", REQUIRED_RECOVERY_DOCS)
    def test_recovery_doc_exists(self, doc):
        fp = RECOVERY_DIR / doc
        assert fp.is_file(), f"missing recovery doc: {doc}"


class TestRecoveryDocSections:
    @pytest.mark.parametrize("doc", REQUIRED_RECOVERY_DOCS)
    def test_recovery_doc_has_required_sections(self, doc):
        fp = RECOVERY_DIR / doc
        if not fp.is_file():
            pytest.skip(f"recovery doc missing: {doc}")
        text = fp.read_text().lower()
        for section in REQUIRED_SECTIONS:
            assert section in text, f"{doc}: missing section '{section}'"


class TestRecoveryDocSafety:
    @pytest.mark.parametrize("doc", REQUIRED_RECOVERY_DOCS)
    def test_recovery_doc_mentions_safety(self, doc):
        fp = RECOVERY_DIR / doc
        if not fp.is_file():
            pytest.skip(f"recovery doc missing: {doc}")
        text = fp.read_text().lower()
        assert "hold" in text, f"{doc}: must mention HOLD"
