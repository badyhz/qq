"""Tests for research static report renderer — T9361-T9800.

HTML renderer, markdown renderer, checklist, required sections.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.research_artifact_browser import (
    build_artifact_browser_index,
    build_review_model,
    validate_artifact_schema,
    artifact_browser_index_to_dict,
    review_model_to_dict,
    schema_validation_to_dict,
)
from core.research_static_report_renderer import (
    CHECKLIST_ITEMS,
    render_html_report,
    render_human_review_checklist,
    render_human_review_checklist_markdown,
    render_markdown_report,
)


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "research_artifact_browser"


def _build_report_data(fixture_name="quality_bundle_pass"):
    """Helper to build report data from fixture."""
    qdir = FIXTURES / fixture_name
    idx = artifact_browser_index_to_dict(build_artifact_browser_index(qdir))
    review = review_model_to_dict(build_review_model(qdir))
    schema = schema_validation_to_dict(validate_artifact_schema(qdir))
    return review, idx, schema


class TestHtmlRendererSections:
    def test_contains_executive_verdict(self):
        review, idx, schema = _build_report_data()
        html = render_html_report(review, idx, schema)
        assert "Executive Verdict" in html

    def test_contains_safety_boundary(self):
        review, idx, schema = _build_report_data()
        html = render_html_report(review, idx, schema)
        assert "Safety Boundary" in html

    def test_contains_artifact_coverage(self):
        review, idx, schema = _build_report_data()
        html = render_html_report(review, idx, schema)
        assert "Artifact Coverage" in html

    def test_contains_quality_scorecard(self):
        review, idx, schema = _build_report_data()
        html = render_html_report(review, idx, schema)
        assert "Quality Scorecard" in html

    def test_contains_blockers_warnings(self):
        review, idx, schema = _build_report_data()
        html = render_html_report(review, idx, schema)
        assert "Blockers" in html
        assert "Warnings" in html

    def test_contains_robustness_labs(self):
        review, idx, schema = _build_report_data()
        html = render_html_report(review, idx, schema)
        assert "Robustness Labs" in html

    def test_contains_negative_controls(self):
        review, idx, schema = _build_report_data()
        html = render_html_report(review, idx, schema)
        assert "Negative Controls" in html

    def test_contains_bootstrap_confidence(self):
        review, idx, schema = _build_report_data()
        html = render_html_report(review, idx, schema)
        assert "Bootstrap Confidence" in html

    def test_contains_regime_segmentation(self):
        review, idx, schema = _build_report_data()
        html = render_html_report(review, idx, schema)
        assert "Regime Segmentation" in html

    def test_contains_portfolio_risk(self):
        review, idx, schema = _build_report_data()
        html = render_html_report(review, idx, schema)
        assert "Portfolio Risk" in html

    def test_contains_reproducibility(self):
        review, idx, schema = _build_report_data()
        html = render_html_report(review, idx, schema)
        assert "Reproducibility" in html

    def test_contains_human_review_checklist(self):
        review, idx, schema = _build_report_data()
        html = render_html_report(review, idx, schema)
        assert "Human Review Checklist" in html

    def test_no_external_resources(self):
        review, idx, schema = _build_report_data()
        html = render_html_report(review, idx, schema)
        assert "cdn" not in html.lower()
        assert "https://" not in html
        assert "http://" not in html

    def test_hold_banner(self):
        review, idx, schema = _build_report_data()
        html = render_html_report(review, idx, schema)
        assert "HOLD" in html

    def test_advisory_disclaimer(self):
        review, idx, schema = _build_report_data()
        html = render_html_report(review, idx, schema)
        assert "ADVISORY ONLY" in html


class TestMarkdownRendererSections:
    def test_contains_executive_verdict(self):
        review, idx, schema = _build_report_data()
        md = render_markdown_report(review, idx, schema)
        assert "Executive Verdict" in md

    def test_contains_safety_boundary(self):
        review, idx, schema = _build_report_data()
        md = render_markdown_report(review, idx, schema)
        assert "Safety Boundary" in md

    def test_contains_artifact_coverage(self):
        review, idx, schema = _build_report_data()
        md = render_markdown_report(review, idx, schema)
        assert "Artifact Coverage" in md

    def test_contains_quality_scorecard(self):
        review, idx, schema = _build_report_data()
        md = render_markdown_report(review, idx, schema)
        assert "Quality Scorecard" in md

    def test_contains_blockers_warnings(self):
        review, idx, schema = _build_report_data()
        md = render_markdown_report(review, idx, schema)
        assert "Blockers" in md
        assert "Warnings" in md

    def test_contains_robustness_labs(self):
        review, idx, schema = _build_report_data()
        md = render_markdown_report(review, idx, schema)
        assert "Robustness Labs" in md

    def test_contains_negative_controls(self):
        review, idx, schema = _build_report_data()
        md = render_markdown_report(review, idx, schema)
        assert "Negative Controls" in md

    def test_contains_bootstrap_confidence(self):
        review, idx, schema = _build_report_data()
        md = render_markdown_report(review, idx, schema)
        assert "Bootstrap Confidence" in md

    def test_contains_regime_segmentation(self):
        review, idx, schema = _build_report_data()
        md = render_markdown_report(review, idx, schema)
        assert "Regime Segmentation" in md

    def test_contains_portfolio_risk(self):
        review, idx, schema = _build_report_data()
        md = render_markdown_report(review, idx, schema)
        assert "Portfolio Risk" in md

    def test_contains_reproducibility(self):
        review, idx, schema = _build_report_data()
        md = render_markdown_report(review, idx, schema)
        assert "Reproducibility" in md

    def test_contains_human_review_checklist(self):
        review, idx, schema = _build_report_data()
        md = render_markdown_report(review, idx, schema)
        assert "Human Review Checklist" in md

    def test_hold_statement(self):
        review, idx, schema = _build_report_data()
        md = render_markdown_report(review, idx, schema)
        assert "HOLD" in md

    def test_advisory_statement(self):
        review, idx, schema = _build_report_data()
        md = render_markdown_report(review, idx, schema)
        assert "Advisory only" in md


class TestChecklistJson:
    def test_checklist_has_all_items(self):
        review, _, _ = _build_report_data()
        cl = render_human_review_checklist(review)
        assert cl["total_items"] == len(CHECKLIST_ITEMS)
        assert len(cl["items"]) == len(CHECKLIST_ITEMS)

    def test_checklist_safety_flags(self):
        review, _, _ = _build_report_data()
        cl = render_human_review_checklist(review)
        assert cl["release_hold"] == "HOLD"
        assert cl["advisory_only"] is True
        assert cl["human_review_required"] is True

    def test_checklist_items_structure(self):
        review, _, _ = _build_report_data()
        cl = render_human_review_checklist(review)
        for item in cl["items"]:
            assert "id" in item
            assert "item" in item
            assert "checked" in item
            assert item["checked"] is False

    def test_checklist_required_items_present(self):
        review, _, _ = _build_report_data()
        cl = render_human_review_checklist(review)
        items_text = " ".join(i["item"] for i in cl["items"])
        assert "safety flags" in items_text
        assert "blockers" in items_text
        assert "negative controls" in items_text
        assert "bootstrap" in items_text
        assert "regime" in items_text
        assert "portfolio overlap" in items_text
        assert "reproducibility" in items_text
        assert "release_hold" in items_text
        assert "HOLD" in items_text
        assert "runtime" in items_text.lower() or "testnet" in items_text.lower()


class TestChecklistMarkdown:
    def test_checklist_md_items(self):
        review, _, _ = _build_report_data()
        md = render_human_review_checklist_markdown(review)
        assert "Human Review Checklist" in md
        assert "[ ]" in md

    def test_checklist_md_safety(self):
        review, _, _ = _build_report_data()
        md = render_human_review_checklist_markdown(review)
        assert "HOLD" in md
        assert "Advisory only" in md

    def test_checklist_md_deterministic(self):
        review, _, _ = _build_report_data()
        r1 = render_human_review_checklist_markdown(review, generated_at="fixed")
        r2 = render_human_review_checklist_markdown(review, generated_at="fixed")
        assert r1 == r2


class TestRendererDeterministic:
    def test_html_deterministic(self):
        review, idx, schema = _build_report_data()
        r1 = render_html_report(review, idx, schema, generated_at="fixed")
        r2 = render_html_report(review, idx, schema, generated_at="fixed")
        assert r1 == r2

    def test_markdown_deterministic(self):
        review, idx, schema = _build_report_data()
        r1 = render_markdown_report(review, idx, schema, generated_at="fixed")
        r2 = render_markdown_report(review, idx, schema, generated_at="fixed")
        assert r1 == r2
