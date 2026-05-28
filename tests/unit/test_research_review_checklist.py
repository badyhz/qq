"""Tests for research review checklist.

Program B tests. No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.research_review_checklist import (
    CHECKLIST_ITEMS,
    build_review_checklist,
    render_checklist_markdown,
    validate_checklist_shape,
)


class TestBuildChecklist:
    def test_contains_required_items(self):
        checklist = build_review_checklist()
        items = checklist["items"]
        required_ids = {i["id"] for i in CHECKLIST_ITEMS}
        actual_ids = {i["id"] for i in items}
        assert required_ids == actual_ids

    def test_all_pending(self):
        checklist = build_review_checklist()
        for item in checklist["items"]:
            assert item["status"] == "PENDING"

    def test_required_fields_present(self):
        checklist = build_review_checklist()
        for item in checklist["items"]:
            assert "id" in item
            assert "label" in item
            assert "required" in item
            assert "status" in item
            assert "evidence_path" in item
            assert "failure_impact" in item

    def test_checklist_shape(self):
        checklist = build_review_checklist()
        valid, errors = validate_checklist_shape(checklist)
        assert valid, f"errors: {errors}"

    def test_deterministic(self):
        c1 = json.dumps(build_review_checklist(), sort_keys=True)
        c2 = json.dumps(build_review_checklist(), sort_keys=True)
        assert c1 == c2


class TestRenderMarkdown:
    def test_contains_safety_boundary(self):
        checklist = build_review_checklist()
        md = render_checklist_markdown(checklist)
        assert "release_hold = HOLD" in md
        assert "advisory_only = True" in md

    def test_contains_allowed_decisions(self):
        checklist = build_review_checklist()
        md = render_checklist_markdown(checklist)
        assert "REJECT" in md
        assert "REQUEST_MORE_RESEARCH" in md
        assert "ACCEPT_ADVISORY_RESEARCH_ONLY" in md

    def test_contains_forbidden_decisions(self):
        checklist = build_review_checklist()
        md = render_checklist_markdown(checklist)
        assert "APPROVE_LIVE" in md
        assert "APPROVE_TESTNET_SUBMIT" in md


class TestValidateShape:
    def test_empty_items_fails(self):
        checklist = {"items": []}
        valid, errors = validate_checklist_shape(checklist)
        assert not valid

    def test_missing_id_fails(self):
        checklist = {"items": [{"label": "test"}]}
        valid, errors = validate_checklist_shape(checklist)
        assert not valid


class TestForbiddenImports:
    FORBIDDEN = ("requests", "httpx", "aiohttp", "websocket", "binance",
                 "ccxt", "live_submit", "testnet_submit")

    def test_no_forbidden_imports(self):
        module_path = Path(__file__).resolve().parent.parent.parent / "core" / "research_review_checklist.py"
        content = module_path.read_text()
        for imp in self.FORBIDDEN:
            assert f"import {imp}" not in content
