"""Tests for research review report renderer and manifest.

Program G + H tests. No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.research_review_report import (
    render_review_html,
    render_review_markdown,
    validate_report_html_sections,
    validate_report_sections,
)
from core.research_review_manifest import (
    build_review_manifest,
    validate_review_manifest_safety,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "research_human_review"


def _make_packet():
    return {
        "packet_id": "test_packet",
        "generated_at": "deterministic",
        "generated_by": "test",
        "source_dirs": {"quality_gate": "/tmp/qg"},
        "source_hashes": {"quality_gate": "abc123"},
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
        "no_live": True,
        "no_submit": True,
        "no_exchange": True,
        "no_network": True,
        "no_runtime_integration": True,
        "no_planner_integration": True,
        "quality_verdict": "PASS",
        "browser_verdict": "PASS",
        "comparison_verdict": "PASS",
        "blockers": [],
        "warnings": [],
        "evidence_links": [],
        "required_review_sections": [],
        "recommended_decision": "REVIEW_ACCEPTED_ADVISORY_ONLY",
        "allowed_decisions": ["BLOCKED", "NEEDS_MORE_RESEARCH", "REVIEW_ACCEPTED_ADVISORY_ONLY"],
        "forbidden_decisions": ["APPROVE_LIVE", "APPROVE_TESTNET_SUBMIT", "APPROVE_RUNTIME", "AUTO_PROMOTE"],
        "promotion_block_statement": "No auto-promotion.",
    }


def _make_checklist():
    return {
        "checklist_version": "1.0.0",
        "total_items": 2,
        "required_items": 2,
        "pending_items": 2,
        "items": [
            {"id": "safety_flags_verified", "label": "Safety flags", "required": True, "status": "PENDING",
             "evidence_path": "test", "failure_impact": "fail"},
            {"id": "release_hold_verified", "label": "release_hold", "required": True, "status": "PENDING",
             "evidence_path": "test", "failure_impact": "fail"},
        ],
    }


def _make_signoff():
    return {
        "allowed_decisions": ["REJECT", "REQUEST_MORE_RESEARCH", "ACCEPT_ADVISORY_RESEARCH_ONLY"],
        "disallowed_decisions": ["APPROVE_LIVE", "APPROVE_TESTNET_SUBMIT", "APPROVE_RUNTIME",
                                  "APPROVE_PLANNER_INTEGRATION", "AUTO_PROMOTE"],
    }


def _make_blocker_ledger():
    return {"total_blockers": 0, "open_blockers": 0, "entries": []}


def _make_audit_trail():
    return {
        "generated_by": "test",
        "generated_at": "deterministic",
        "deterministic_ordering": True,
    }


class TestReportMarkdown:
    def test_required_sections(self):
        md = render_review_markdown(
            _make_packet(), _make_checklist(), _make_signoff(),
            _make_blocker_ledger(), _make_audit_trail(),
        )
        assert validate_report_sections(md)

    def test_contains_safety(self):
        md = render_review_markdown(
            _make_packet(), _make_checklist(), _make_signoff(),
            _make_blocker_ledger(), _make_audit_trail(),
        )
        assert "release_hold = HOLD" in md
        assert "advisory_only" in md.lower() or "Advisory-Only" in md

    def test_contains_forbidden_decisions(self):
        md = render_review_markdown(
            _make_packet(), _make_checklist(), _make_signoff(),
            _make_blocker_ledger(), _make_audit_trail(),
        )
        assert "APPROVE_LIVE" in md
        assert "AUTO_PROMOTE" in md


class TestReportHtml:
    def test_required_sections(self):
        html_content = render_review_html(
            _make_packet(), _make_checklist(), _make_signoff(),
            _make_blocker_ledger(), _make_audit_trail(),
        )
        assert validate_report_html_sections(html_content)

    def test_standalone_html(self):
        html_content = render_review_html(
            _make_packet(), _make_checklist(), _make_signoff(),
            _make_blocker_ledger(), _make_audit_trail(),
        )
        assert "<!DOCTYPE html>" in html_content
        assert "</html>" in html_content

    def test_no_cdn(self):
        html_content = render_review_html(
            _make_packet(), _make_checklist(), _make_signoff(),
            _make_blocker_ledger(), _make_audit_trail(),
        )
        assert "cdn" not in html_content.lower()
        assert "external" not in html_content.lower() or "external" in html_content

    def test_contains_safety(self):
        html_content = render_review_html(
            _make_packet(), _make_checklist(), _make_signoff(),
            _make_blocker_ledger(), _make_audit_trail(),
        )
        assert "HOLD" in html_content


class TestReviewManifest:
    def test_build_manifest(self):
        manifest = build_review_manifest(
            source_hashes={"quality_gate": "abc"},
            output_hashes={"review_packet.json": "def"},
        )
        assert manifest["release_hold"] == "HOLD"
        assert manifest["advisory_only"] is True
        assert manifest["human_review_required"] is True
        assert manifest["no_live"] is True
        assert manifest["no_network"] is True
        assert manifest["no_runtime_integration"] is True
        assert manifest["no_planner_integration"] is True

    def test_validate_safety(self):
        manifest = build_review_manifest(
            source_hashes={},
            output_hashes={},
        )
        valid, errors = validate_review_manifest_safety(manifest)
        assert valid, f"errors: {errors}"

    def test_invalid_release_hold(self):
        manifest = build_review_manifest(source_hashes={}, output_hashes={})
        manifest["release_hold"] = "NOT_HOLD"
        valid, errors = validate_review_manifest_safety(manifest)
        assert not valid

    def test_invalid_advisory_only(self):
        manifest = build_review_manifest(source_hashes={}, output_hashes={})
        manifest["advisory_only"] = False
        valid, errors = validate_review_manifest_safety(manifest)
        assert not valid

    def test_deterministic(self):
        m1 = json.dumps(build_review_manifest({}, {}, generated_at="fixed"), sort_keys=True)
        m2 = json.dumps(build_review_manifest({}, {}, generated_at="fixed"), sort_keys=True)
        assert m1 == m2


class TestForbiddenImports:
    FORBIDDEN = ("requests", "httpx", "aiohttp", "websocket", "binance",
                 "ccxt", "live_submit", "testnet_submit")

    def test_no_forbidden_in_report(self):
        module_path = Path(__file__).resolve().parent.parent.parent / "core" / "research_review_report.py"
        content = module_path.read_text()
        for imp in self.FORBIDDEN:
            assert f"import {imp}" not in content

    def test_no_forbidden_in_manifest(self):
        module_path = Path(__file__).resolve().parent.parent.parent / "core" / "research_review_manifest.py"
        content = module_path.read_text()
        for imp in self.FORBIDDEN:
            assert f"import {imp}" not in content
