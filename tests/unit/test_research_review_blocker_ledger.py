"""Tests for research review blocker resolution ledger.

Program E tests. No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.research_review_blocker_ledger import (
    ALLOWED_BLOCKER_STATUSES,
    FORBIDDEN_BLOCKER_STATUSES,
    build_blocker_ledger,
    render_blocker_ledger_markdown,
    validate_blocker_ledger,
)


class TestBuildLedger:
    def test_from_blockers(self):
        blockers = [
            {"blocker_id": "B1", "source": "quality_gate", "severity": "CRITICAL"},
            {"blocker_id": "B2", "source": "comparison", "severity": "WARNING"},
        ]
        ledger = build_blocker_ledger(blockers)
        assert ledger["total_blockers"] == 2
        assert ledger["open_blockers"] == 2
        assert len(ledger["entries"]) == 2

    def test_empty_blockers(self):
        ledger = build_blocker_ledger([])
        assert ledger["total_blockers"] == 0
        assert ledger["open_blockers"] == 0

    def test_allowed_statuses(self):
        for status in ALLOWED_BLOCKER_STATUSES:
            assert status in ALLOWED_BLOCKER_STATUSES

    def test_forbidden_statuses_not_in_allowed(self):
        for status in FORBIDDEN_BLOCKER_STATUSES:
            assert status not in ALLOWED_BLOCKER_STATUSES

    def test_deterministic(self):
        blockers = [{"blocker_id": "B1", "source": "test", "severity": "CRITICAL"}]
        l1 = json.dumps(build_blocker_ledger(blockers, "fixed"), sort_keys=True)
        l2 = json.dumps(build_blocker_ledger(blockers, "fixed"), sort_keys=True)
        assert l1 == l2


class TestValidateLedger:
    def test_valid_open_ledger(self):
        blockers = [{"blocker_id": "B1", "source": "test", "severity": "CRITICAL"}]
        ledger = build_blocker_ledger(blockers)
        valid, errors = validate_blocker_ledger(ledger)
        assert valid, f"errors: {errors}"

    def test_resolved_for_live_rejected(self):
        ledger = {
            "entries": [{
                "blocker_id": "B1",
                "source": "test",
                "severity": "CRITICAL",
                "status": "RESOLVED_FOR_LIVE",
                "resolution_note": "fixed",
                "resolved_by": "tester",
            }]
        }
        valid, errors = validate_blocker_ledger(ledger)
        assert not valid
        assert any("RESOLVED_FOR_LIVE" in e for e in errors)

    def test_resolved_for_testnet_rejected(self):
        ledger = {
            "entries": [{
                "blocker_id": "B1",
                "source": "test",
                "severity": "CRITICAL",
                "status": "RESOLVED_FOR_TESTNET",
                "resolution_note": "fixed",
                "resolved_by": "tester",
            }]
        }
        valid, errors = validate_blocker_ledger(ledger)
        assert not valid

    def test_auto_cleared_rejected(self):
        ledger = {
            "entries": [{
                "blocker_id": "B1",
                "source": "test",
                "severity": "CRITICAL",
                "status": "AUTO_CLEARED",
                "resolution_note": "auto",
                "resolved_by": "system",
            }]
        }
        valid, errors = validate_blocker_ledger(ledger)
        assert not valid

    def test_resolved_needs_resolved_by(self):
        ledger = {
            "entries": [{
                "blocker_id": "B1",
                "source": "test",
                "severity": "CRITICAL",
                "status": "RESOLVED_ADVISORY_ONLY",
                "resolution_note": "fixed",
                "resolved_by": "",
            }]
        }
        valid, errors = validate_blocker_ledger(ledger)
        assert not valid

    def test_resolved_needs_resolution_note(self):
        ledger = {
            "entries": [{
                "blocker_id": "B1",
                "source": "test",
                "severity": "CRITICAL",
                "status": "RESOLVED_ADVISORY_ONLY",
                "resolution_note": "",
                "resolved_by": "tester",
            }]
        }
        valid, errors = validate_blocker_ledger(ledger)
        assert not valid


class TestRenderMarkdown:
    def test_contains_safety_boundary(self):
        ledger = build_blocker_ledger([])
        md = render_blocker_ledger_markdown(ledger)
        assert "RESOLVED_ADVISORY_ONLY" in md
        assert "RESOLVED_FOR_LIVE" in md

    def test_contains_entries(self):
        blockers = [{"blocker_id": "B1", "source": "test", "severity": "CRITICAL"}]
        ledger = build_blocker_ledger(blockers)
        md = render_blocker_ledger_markdown(ledger)
        assert "B1" in md


class TestForbiddenImports:
    FORBIDDEN = ("requests", "httpx", "aiohttp", "websocket", "binance",
                 "ccxt", "live_submit", "testnet_submit")

    def test_no_forbidden_imports(self):
        module_path = Path(__file__).resolve().parent.parent.parent / "core" / "research_review_blocker_ledger.py"
        content = module_path.read_text()
        for imp in self.FORBIDDEN:
            assert f"import {imp}" not in content
