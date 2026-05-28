"""Tests for research review packet builder.

Program A tests. No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.research_review_packet import (
    ALLOWED_RECOMMENDED_DECISIONS,
    FORBIDDEN_DECISIONS,
    build_review_packet,
    compute_source_hashes,
    determine_recommended_decision,
    extract_blockers_from_comparison,
    extract_blockers_from_quality,
    extract_verdict_from_dir,
    validate_review_packet_safety,
)


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "research_human_review"


class TestExtractVerdict:
    def test_pass_verdict(self):
        d = FIXTURES / "source_quality_gate"
        assert extract_verdict_from_dir(d) == "PASS"

    def test_missing_manifest(self, tmp_path):
        assert extract_verdict_from_dir(tmp_path) == "MISSING"

    def test_invalid_safety_verdict(self):
        d = FIXTURES / "invalid_safety"
        assert extract_verdict_from_dir(d) == "INVALID_SAFETY"

    def test_corrupted_verdict(self):
        d = FIXTURES / "corrupted"
        assert extract_verdict_from_dir(d) == "CORRUPTED"


class TestExtractBlockers:
    def test_quality_gate_pass(self):
        d = FIXTURES / "source_quality_gate"
        blockers = extract_blockers_from_quality(d)
        assert all(b.get("severity") != "CRITICAL" for b in blockers)

    def test_quality_gate_missing(self, tmp_path):
        blockers = extract_blockers_from_quality(tmp_path)
        assert any(b["blocker_id"] == "QUALITY_SUMMARY_MISSING" for b in blockers)

    def test_quality_gate_fail(self, tmp_path):
        (tmp_path / "quality_gate_summary.json").write_text(
            json.dumps({"overall_verdict": "FAIL"})
        )
        blockers = extract_blockers_from_quality(tmp_path)
        assert any(b["blocker_id"] == "QUALITY_GATE_FAIL" for b in blockers)

    def test_quality_gate_partial(self, tmp_path):
        (tmp_path / "quality_gate_summary.json").write_text(
            json.dumps({"overall_verdict": "PARTIAL"})
        )
        blockers = extract_blockers_from_quality(tmp_path)
        assert any(b["blocker_id"] == "QUALITY_GATE_PARTIAL" for b in blockers)

    def test_quality_gate_corrupted(self, tmp_path):
        (tmp_path / "quality_gate_summary.json").write_text("not json")
        blockers = extract_blockers_from_quality(tmp_path)
        assert any(b["blocker_id"] == "QUALITY_SUMMARY_CORRUPTED" for b in blockers)

    def test_comparison_no_regression(self):
        d = FIXTURES / "source_comparison"
        blockers = extract_blockers_from_comparison(d)
        assert not any(b.get("blocker_id") == "COMPARISON_SAFETY_REGRESSION" for b in blockers)

    def test_comparison_missing(self, tmp_path):
        blockers = extract_blockers_from_comparison(tmp_path)
        assert any(b["blocker_id"] == "COMPARISON_REGRESSION_MISSING" for b in blockers)

    def test_comparison_safety_regression(self, tmp_path):
        (tmp_path / "regression_report.json").write_text(
            json.dumps({"has_any_safety_regression": True})
        )
        blockers = extract_blockers_from_comparison(tmp_path)
        assert any(b["blocker_id"] == "COMPARISON_SAFETY_REGRESSION" for b in blockers)


class TestDetermineDecision:
    def test_no_blockers(self):
        assert determine_recommended_decision([]) == "REVIEW_ACCEPTED_ADVISORY_ONLY"

    def test_warning_only(self):
        blockers = [{"severity": "WARNING"}]
        assert determine_recommended_decision(blockers) == "NEEDS_MORE_RESEARCH"

    def test_critical(self):
        blockers = [{"severity": "CRITICAL"}]
        assert determine_recommended_decision(blockers) == "BLOCKED"


class TestBuildPacket:
    def test_normal_build(self):
        source_dirs = {
            "quality_gate": FIXTURES / "source_quality_gate",
            "artifact_browser": FIXTURES / "source_artifact_browser",
            "comparison_analytics": FIXTURES / "source_comparison",
        }
        hashes = compute_source_hashes(source_dirs)
        packet = build_review_packet(
            quality_dir=source_dirs["quality_gate"],
            browser_dir=source_dirs["artifact_browser"],
            comparison_dir=source_dirs["comparison_analytics"],
            source_hashes=hashes,
        )
        assert packet["release_hold"] == "HOLD"
        assert packet["advisory_only"] is True
        assert packet["human_review_required"] is True
        assert packet["no_network"] is True
        assert packet["no_live"] is True
        assert "packet_id" in packet
        assert "blockers" in packet
        assert "allowed_decisions" in packet
        assert "forbidden_decisions" in packet

    def test_packet_contains_forbidden_decisions(self):
        source_dirs = {
            "quality_gate": FIXTURES / "source_quality_gate",
            "artifact_browser": FIXTURES / "source_artifact_browser",
            "comparison_analytics": FIXTURES / "source_comparison",
        }
        hashes = compute_source_hashes(source_dirs)
        packet = build_review_packet(
            quality_dir=source_dirs["quality_gate"],
            browser_dir=source_dirs["artifact_browser"],
            comparison_dir=source_dirs["comparison_analytics"],
            source_hashes=hashes,
        )
        for fd in FORBIDDEN_DECISIONS:
            assert fd in packet["forbidden_decisions"]
        for fd in FORBIDDEN_DECISIONS:
            assert fd not in packet["allowed_decisions"]

    def test_packet_shape(self):
        source_dirs = {
            "quality_gate": FIXTURES / "source_quality_gate",
            "artifact_browser": FIXTURES / "source_artifact_browser",
            "comparison_analytics": FIXTURES / "source_comparison",
        }
        hashes = compute_source_hashes(source_dirs)
        packet = build_review_packet(
            quality_dir=source_dirs["quality_gate"],
            browser_dir=source_dirs["artifact_browser"],
            comparison_dir=source_dirs["comparison_analytics"],
            source_hashes=hashes,
        )
        required_keys = [
            "packet_id", "generated_at", "generated_by",
            "source_dirs", "source_hashes",
            "release_hold", "advisory_only", "human_review_required",
            "no_live", "no_submit", "no_exchange", "no_network",
            "no_runtime_integration", "no_planner_integration",
            "quality_verdict", "browser_verdict", "comparison_verdict",
            "blockers", "warnings", "evidence_links",
            "required_review_sections", "recommended_decision",
            "allowed_decisions", "forbidden_decisions",
            "promotion_block_statement",
        ]
        for key in required_keys:
            assert key in packet, f"missing key: {key}"


class TestValidatePacketSafety:
    def test_valid_packet(self):
        source_dirs = {
            "quality_gate": FIXTURES / "source_quality_gate",
            "artifact_browser": FIXTURES / "source_artifact_browser",
            "comparison_analytics": FIXTURES / "source_comparison",
        }
        hashes = compute_source_hashes(source_dirs)
        packet = build_review_packet(
            quality_dir=source_dirs["quality_gate"],
            browser_dir=source_dirs["artifact_browser"],
            comparison_dir=source_dirs["comparison_analytics"],
            source_hashes=hashes,
        )
        valid, errors = validate_review_packet_safety(packet)
        assert valid, f"errors: {errors}"

    def test_invalid_release_hold(self):
        source_dirs = {
            "quality_gate": FIXTURES / "source_quality_gate",
            "artifact_browser": FIXTURES / "source_artifact_browser",
            "comparison_analytics": FIXTURES / "source_comparison",
        }
        hashes = compute_source_hashes(source_dirs)
        packet = build_review_packet(
            quality_dir=source_dirs["quality_gate"],
            browser_dir=source_dirs["artifact_browser"],
            comparison_dir=source_dirs["comparison_analytics"],
            source_hashes=hashes,
        )
        packet["release_hold"] = "NOT_HOLD"
        valid, errors = validate_review_packet_safety(packet)
        assert not valid

    def test_forbidden_in_allowed(self):
        source_dirs = {
            "quality_gate": FIXTURES / "source_quality_gate",
            "artifact_browser": FIXTURES / "source_artifact_browser",
            "comparison_analytics": FIXTURES / "source_comparison",
        }
        hashes = compute_source_hashes(source_dirs)
        packet = build_review_packet(
            quality_dir=source_dirs["quality_gate"],
            browser_dir=source_dirs["artifact_browser"],
            comparison_dir=source_dirs["comparison_analytics"],
            source_hashes=hashes,
        )
        packet["allowed_decisions"].append("APPROVE_LIVE")
        valid, errors = validate_review_packet_safety(packet)
        assert not valid

    def test_deterministic_output(self):
        source_dirs = {
            "quality_gate": FIXTURES / "source_quality_gate",
            "artifact_browser": FIXTURES / "source_artifact_browser",
            "comparison_analytics": FIXTURES / "source_comparison",
        }
        hashes = compute_source_hashes(source_dirs)
        p1 = build_review_packet(
            quality_dir=source_dirs["quality_gate"],
            browser_dir=source_dirs["artifact_browser"],
            comparison_dir=source_dirs["comparison_analytics"],
            source_hashes=hashes,
            generated_at="fixed",
        )
        p2 = build_review_packet(
            quality_dir=source_dirs["quality_gate"],
            browser_dir=source_dirs["artifact_browser"],
            comparison_dir=source_dirs["comparison_analytics"],
            source_hashes=hashes,
            generated_at="fixed",
        )
        assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True)


class TestForbiddenImports:
    FORBIDDEN = ("requests", "httpx", "aiohttp", "websocket", "binance",
                 "ccxt", "live_submit", "testnet_submit")

    def test_no_forbidden_imports_in_packet_module(self):
        module_path = Path(__file__).resolve().parent.parent.parent / "core" / "research_review_packet.py"
        content = module_path.read_text()
        for imp in self.FORBIDDEN:
            pattern = f"import {imp}"
            assert pattern not in content, f"forbidden import {imp} in {module_path.name}"
