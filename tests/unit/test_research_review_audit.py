"""Tests for research review audit trail.

Program F tests. No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.research_review_audit_trail import (
    build_audit_trail,
    compute_output_hashes_from_dict,
    render_audit_trail_markdown,
    validate_audit_trail_safety,
)


class TestBuildAuditTrail:
    def test_safety_flags(self):
        trail = build_audit_trail(
            input_artifact_hashes={"a.json": "hash1"},
            output_artifact_hashes={"b.json": "hash2"},
            command_args=["--strict"],
        )
        assert trail["release_hold"] == "HOLD"
        assert trail["advisory_only"] is True
        assert trail["human_review_required"] is True
        assert trail["no_live"] is True
        assert trail["no_submit"] is True
        assert trail["no_exchange"] is True
        assert trail["no_network"] is True
        assert trail["no_runtime_integration"] is True
        assert trail["no_planner_integration"] is True
        assert trail["no_auto_promotion"] is True

    def test_deterministic_ordering(self):
        trail = build_audit_trail(
            input_artifact_hashes={},
            output_artifact_hashes={},
            command_args=[],
        )
        assert trail["deterministic_ordering"] is True

    def test_validate_safety(self):
        trail = build_audit_trail(
            input_artifact_hashes={},
            output_artifact_hashes={},
            command_args=[],
        )
        valid, errors = validate_audit_trail_safety(trail)
        assert valid, f"errors: {errors}"

    def test_invalid_safety(self):
        trail = build_audit_trail(
            input_artifact_hashes={},
            output_artifact_hashes={},
            command_args=[],
        )
        trail["release_hold"] = "NOT_HOLD"
        valid, errors = validate_audit_trail_safety(trail)
        assert not valid

    def test_deterministic(self):
        t1 = json.dumps(build_audit_trail({}, {}, ["--test"], generated_at="fixed"), sort_keys=True)
        t2 = json.dumps(build_audit_trail({}, {}, ["--test"], generated_at="fixed"), sort_keys=True)
        assert t1 == t2

    def test_hashes_stable(self):
        """Audit trail hashes are stable across runs."""
        data = {"key": "value"}
        h1 = compute_output_hashes_from_dict({"test.json": data})
        h2 = compute_output_hashes_from_dict({"test.json": data})
        assert h1 == h2


class TestRenderMarkdown:
    def test_contains_safety_flags(self):
        trail = build_audit_trail({}, {}, ["--test"])
        md = render_audit_trail_markdown(trail)
        assert "release_hold = HOLD" in md
        assert "advisory_only = True" in md
        assert "no_auto_promotion = True" in md

    def test_contains_command_args(self):
        trail = build_audit_trail({}, {}, ["--test", "--strict"])
        md = render_audit_trail_markdown(trail)
        assert "--test" in md
        assert "--strict" in md


class TestForbiddenImports:
    FORBIDDEN = ("requests", "httpx", "aiohttp", "websocket", "binance",
                 "ccxt", "live_submit", "testnet_submit")

    def test_no_forbidden_imports(self):
        module_path = Path(__file__).resolve().parent.parent.parent / "core" / "research_review_audit_trail.py"
        content = module_path.read_text()
        for imp in self.FORBIDDEN:
            assert f"import {imp}" not in content
