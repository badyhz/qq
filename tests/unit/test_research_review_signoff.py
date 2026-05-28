"""Tests for research review signoff template and validator.

Program C + D tests. No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.research_review_signoff import (
    ALLOWED_MANUAL_DECISIONS,
    DISALLOWED_DECISIONS,
    build_signoff_template,
    render_signoff_markdown,
    validate_completed_signoff,
    validate_signoff_template_safety,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "research_human_review"


class TestBuildTemplate:
    def test_allowed_decisions_exclude_live(self):
        template = build_signoff_template()
        for d in DISALLOWED_DECISIONS:
            assert d not in template["allowed_decisions"]

    def test_disallowed_decisions_present(self):
        template = build_signoff_template()
        for d in DISALLOWED_DECISIONS:
            assert d in template["disallowed_decisions"]

    def test_template_safety(self):
        template = build_signoff_template()
        valid, errors = validate_signoff_template_safety(template)
        assert valid, f"errors: {errors}"

    def test_template_shape(self):
        template = build_signoff_template(packet_id="test_123")
        assert template["reviewed_packet_id"] == "test_123"
        assert template["confirmation_release_hold_remains_HOLD"] is False
        assert template["confirmation_advisory_only"] is False
        assert template["confirmation_no_live_testnet_runtime"] is False

    def test_deterministic(self):
        t1 = json.dumps(build_signoff_template(), sort_keys=True)
        t2 = json.dumps(build_signoff_template(), sort_keys=True)
        assert t1 == t2


class TestRenderMarkdown:
    def test_contains_allowed_decisions(self):
        template = build_signoff_template()
        md = render_signoff_markdown(template)
        for d in ALLOWED_MANUAL_DECISIONS:
            assert d in md

    def test_contains_forbidden_decisions(self):
        template = build_signoff_template()
        md = render_signoff_markdown(template)
        for d in DISALLOWED_DECISIONS:
            assert d in md


class TestValidateCompletedSignoff:
    def test_valid_request_more_research(self):
        path = FIXTURES / "signoff_valid_request_more_research" / "review_signoff_completed.json"
        signoff = json.loads(path.read_text())
        valid, errors = validate_completed_signoff(signoff)
        assert valid, f"errors: {errors}"

    def test_invalid_approve_live(self):
        path = FIXTURES / "signoff_invalid_approve_live" / "review_signoff_completed.json"
        signoff = json.loads(path.read_text())
        valid, errors = validate_completed_signoff(signoff)
        assert not valid
        assert any("APPROVE_LIVE" in e for e in errors)

    def test_invalid_unresolved_blockers(self):
        path = FIXTURES / "signoff_invalid_unresolved_blockers" / "review_signoff_completed.json"
        signoff = json.loads(path.read_text())
        valid, errors = validate_completed_signoff(signoff)
        assert not valid
        assert any("critical" in e.lower() or "blocker" in e.lower() for e in errors)

    def test_missing_reviewer_name(self):
        signoff = {
            "decision": "REJECT",
            "confirmation_release_hold_remains_HOLD": True,
            "confirmation_advisory_only": True,
            "confirmation_no_live_testnet_runtime": True,
        }
        valid, errors = validate_completed_signoff(signoff)
        assert not valid
        assert any("reviewer_name" in e for e in errors)

    def test_missing_decision(self):
        signoff = {
            "reviewer_name": "Test",
            "confirmation_release_hold_remains_HOLD": True,
            "confirmation_advisory_only": True,
            "confirmation_no_live_testnet_runtime": True,
        }
        valid, errors = validate_completed_signoff(signoff)
        assert not valid
        assert any("decision" in e for e in errors)

    def test_accept_advisory_with_critical_blockers_fails(self):
        signoff = {
            "reviewer_name": "Test",
            "decision": "ACCEPT_ADVISORY_RESEARCH_ONLY",
            "unresolved_blockers": [{"blocker_id": "X", "severity": "CRITICAL"}],
            "confirmation_release_hold_remains_HOLD": True,
            "confirmation_advisory_only": True,
            "confirmation_no_live_testnet_runtime": True,
        }
        valid, errors = validate_completed_signoff(signoff)
        assert not valid

    def test_request_more_research_with_unresolved_blockers_ok(self):
        signoff = {
            "reviewer_name": "Test",
            "decision": "REQUEST_MORE_RESEARCH",
            "unresolved_blockers": [{"blocker_id": "X", "severity": "WARNING"}],
            "confirmation_release_hold_remains_HOLD": True,
            "confirmation_advisory_only": True,
            "confirmation_no_live_testnet_runtime": True,
        }
        valid, errors = validate_completed_signoff(signoff)
        assert valid, f"errors: {errors}"

    def test_reject_with_unresolved_blockers_ok(self):
        signoff = {
            "reviewer_name": "Test",
            "decision": "REJECT",
            "unresolved_blockers": [{"blocker_id": "X", "severity": "CRITICAL"}],
            "confirmation_release_hold_remains_HOLD": True,
            "confirmation_advisory_only": True,
            "confirmation_no_live_testnet_runtime": True,
        }
        valid, errors = validate_completed_signoff(signoff)
        assert valid, f"errors: {errors}"

    def test_confirmation_flags_required(self):
        signoff = {
            "reviewer_name": "Test",
            "decision": "REJECT",
            "confirmation_release_hold_remains_HOLD": False,
            "confirmation_advisory_only": True,
            "confirmation_no_live_testnet_runtime": True,
        }
        valid, errors = validate_completed_signoff(signoff)
        assert not valid

    def test_never_produces_live_approval(self):
        """Prove no valid signoff can have APPROVE_LIVE as decision."""
        for decision in ALLOWED_MANUAL_DECISIONS:
            signoff = {
                "reviewer_name": "Test",
                "decision": decision,
                "confirmation_release_hold_remains_HOLD": True,
                "confirmation_advisory_only": True,
                "confirmation_no_live_testnet_runtime": True,
            }
            valid, _ = validate_completed_signoff(signoff)
            if valid:
                assert decision not in DISALLOWED_DECISIONS


class TestForbiddenImports:
    FORBIDDEN = ("requests", "httpx", "aiohttp", "websocket", "binance",
                 "ccxt", "live_submit", "testnet_submit")

    def test_no_forbidden_imports(self):
        module_path = Path(__file__).resolve().parent.parent.parent / "core" / "research_review_signoff.py"
        content = module_path.read_text()
        for imp in self.FORBIDDEN:
            assert f"import {imp}" not in content
