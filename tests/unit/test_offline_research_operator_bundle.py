"""Tests for offline research operator bundle builder.

No network. No exchange. No runtime. No planner. Advisory only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.build_offline_research_operator_bundle import (
    build_command_cheatsheet,
    build_experiment_catalog_summary,
    build_html,
    build_index,
    build_manifest,
    build_markdown,
    build_recovery_index,
    build_safety_cheatsheet,
)

DOCS_ROOT = Path(__file__).resolve().parent.parent.parent / "docs"
CATALOG_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "offline_research_experiment_library" / "experiment_catalog.json"


class TestBuildIndex:
    def test_index_has_required_keys(self):
        index = build_index(DOCS_ROOT, CATALOG_PATH)
        assert "version" in index
        assert "release_hold" in index
        assert index["release_hold"] == "HOLD"
        assert index["advisory_only"] is True
        assert "operator_manuals" in index
        assert "runbooks" in index
        assert "checklists" in index
        assert "recovery_docs" in index
        assert "experiment_count" in index

    def test_experiment_count(self):
        index = build_index(DOCS_ROOT, CATALOG_PATH)
        assert index["experiment_count"] >= 20


class TestBuildManifest:
    def test_manifest_has_doc_counts(self):
        index = build_index(DOCS_ROOT, CATALOG_PATH)
        manifest = build_manifest(index)
        assert "doc_counts" in manifest
        assert manifest["release_hold"] == "HOLD"


class TestBuildMarkdown:
    def test_markdown_has_safety_section(self):
        index = build_index(DOCS_ROOT, CATALOG_PATH)
        md = build_markdown(index)
        assert "HOLD" in md
        assert "advisory" in md.lower()
        assert "safety" in md.lower()


class TestBuildHtml:
    def test_html_standalone(self):
        index = build_index(DOCS_ROOT, CATALOG_PATH)
        html = build_html(index)
        assert "<!DOCTYPE html>" in html
        assert "HOLD" in html
        # No external JS/CDN
        assert "cdn" not in html.lower()
        assert "src=\"http" not in html.lower()

    def test_html_has_safety_boundary(self):
        index = build_index(DOCS_ROOT, CATALOG_PATH)
        html = build_html(index)
        assert "Safety Boundary" in html
        assert "no auto-promotion" in html.lower() or "no auto_promotion" in html.lower()


class TestCheatsheets:
    def test_command_cheatsheet_has_commands(self):
        sheet = build_command_cheatsheet()
        assert "validate_offline_research_experiment_library.py" in sheet
        assert "validate_offline_research_stack_docs.py" in sheet
        assert "--release-hold HOLD" in sheet

    def test_safety_cheatsheet_has_safety(self):
        sheet = build_safety_cheatsheet()
        assert "HOLD" in sheet
        assert "advisory" in sheet.lower()
        assert "forbidden" in sheet.lower()

    def test_recovery_index_has_links(self):
        idx = build_recovery_index()
        assert "recovery/" in idx
        assert "missing_quality_artifacts" in idx


class TestExperimentCatalogSummary:
    def test_summary_has_experiments(self):
        summary = build_experiment_catalog_summary(CATALOG_PATH)
        assert "baseline_major_5m_15m" in summary
        assert "HOLD" in summary
