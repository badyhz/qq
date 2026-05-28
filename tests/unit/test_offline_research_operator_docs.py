"""Tests for offline research operator documentation.

No network. No exchange. No runtime. No planner. Advisory only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DOCS_ROOT = Path(__file__).resolve().parent.parent.parent / "docs"
OPERATOR_DIR = DOCS_ROOT / "operator_manuals"


class TestOperatorManualsExist:
    def test_operator_manual_exists(self):
        assert (OPERATOR_DIR / "offline_research_stack_operator_manual.md").is_file()

    def test_quickstart_exists(self):
        assert (OPERATOR_DIR / "offline_research_stack_quickstart.md").is_file()

    def test_command_reference_exists(self):
        assert (OPERATOR_DIR / "offline_research_stack_command_reference.md").is_file()

    def test_artifact_reference_exists(self):
        assert (OPERATOR_DIR / "offline_research_stack_artifact_reference.md").is_file()

    def test_safety_manual_exists(self):
        assert (OPERATOR_DIR / "offline_research_stack_safety_manual.md").is_file()

    def test_troubleshooting_exists(self):
        assert (OPERATOR_DIR / "offline_research_stack_troubleshooting.md").is_file()

    def test_faq_exists(self):
        assert (OPERATOR_DIR / "offline_research_stack_faq.md").is_file()


class TestOperatorManualSections:
    REQUIRED_SECTIONS = [
        "system overview",
        "phase history",
        "tags",
        "commands",
        "artifact map",
        "report map",
        "fixture map",
        "safety boundary",
        "untracked",
        "full offline pipeline",
        "inspect output",
        "compare bundles",
        "human review packet",
        "signoff",
        "recover",
        "corrupted",
        "quality gate",
        "deterministic",
        "what not to do",
        "next safe extension",
    ]

    def test_operator_manual_has_sections(self):
        manual = OPERATOR_DIR / "offline_research_stack_operator_manual.md"
        assert manual.is_file(), "operator manual missing"
        text = manual.read_text().lower()
        for section in self.REQUIRED_SECTIONS:
            assert section.lower() in text, f"missing section: {section}"


class TestSafetyManualContent:
    def test_safety_manual_mentions_hold(self):
        fp = OPERATOR_DIR / "offline_research_stack_safety_manual.md"
        assert fp.is_file()
        text = fp.read_text().lower()
        assert "hold" in text

    def test_safety_manual_mentions_advisory(self):
        fp = OPERATOR_DIR / "offline_research_stack_safety_manual.md"
        assert fp.is_file()
        text = fp.read_text().lower()
        assert "advisory" in text

    def test_safety_manual_mentions_no_live(self):
        fp = OPERATOR_DIR / "offline_research_stack_safety_manual.md"
        assert fp.is_file()
        text = fp.read_text().lower()
        assert "no_live" in text or "no live" in text

    def test_safety_manual_mentions_no_auto_promotion(self):
        fp = OPERATOR_DIR / "offline_research_stack_safety_manual.md"
        assert fp.is_file()
        text = fp.read_text().lower()
        assert "auto_promotion" in text or "auto-promotion" in text or "auto promotion" in text

    def test_safety_manual_mentions_untracked(self):
        fp = OPERATOR_DIR / "offline_research_stack_safety_manual.md"
        assert fp.is_file()
        text = fp.read_text().lower()
        assert "untracked" in text
