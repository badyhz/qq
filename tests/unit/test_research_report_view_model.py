"""Tests for research report view model — T9361-T9800.

Extract blockers, warnings, safety flags. Handle missing optional metrics.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from core.research_artifact_browser import (
    build_review_model,
    review_model_to_dict,
    review_model_to_json,
)


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "research_artifact_browser"


class TestViewModelNormal:
    def test_pass_bundle_verdict(self):
        m = build_review_model(FIXTURES / "quality_bundle_pass")
        assert m.verdict == "PASS"

    def test_pass_bundle_score(self):
        m = build_review_model(FIXTURES / "quality_bundle_pass")
        assert m.composite_score == pytest.approx(0.85)

    def test_pass_bundle_completeness(self):
        m = build_review_model(FIXTURES / "quality_bundle_pass")
        assert m.evidence_completeness == pytest.approx(1.0)


class TestViewModelBlockersWarnings:
    def test_extract_warnings(self):
        m = build_review_model(FIXTURES / "quality_bundle_pass")
        assert "bootstrap_below_threshold" in m.warnings

    def test_extract_blockers_empty(self):
        m = build_review_model(FIXTURES / "quality_bundle_pass")
        assert len(m.blockers) == 0

    def test_changed_bundle_more_warnings(self):
        m = build_review_model(FIXTURES / "quality_bundle_changed")
        assert len(m.warnings) > 1

    def test_invalid_safety_bundle_has_blockers(self):
        m = build_review_model(FIXTURES / "quality_bundle_invalid_safety")
        assert len(m.blockers) > 0


class TestViewModelSafetyFlags:
    def test_safety_flags_complete(self):
        m = build_review_model(FIXTURES / "quality_bundle_pass")
        required = [
            "release_hold_is_HOLD", "no_live", "no_submit", "no_exchange",
            "no_runtime_integration", "no_planner_integration", "no_network",
            "advisory_only", "human_review_required", "strict_mode",
        ]
        for flag in required:
            assert flag in m.safety_flags, f"Missing: {flag}"

    def test_pass_bundle_all_safety_true(self):
        m = build_review_model(FIXTURES / "quality_bundle_pass")
        for k, v in m.safety_flags.items():
            assert v is True, f"Flag {k} is {v}"

    def test_invalid_safety_bundle_flags_false(self):
        m = build_review_model(FIXTURES / "quality_bundle_invalid_safety")
        assert m.safety_flags["release_hold_is_HOLD"] is False
        assert m.safety_flags["advisory_only"] is False


class TestViewModelSubSummaries:
    def test_strategy_robustness_summary(self):
        m = build_review_model(FIXTURES / "quality_bundle_pass")
        assert "verdict" in m.strategy_robustness_summary

    def test_negative_control_summary(self):
        m = build_review_model(FIXTURES / "quality_bundle_pass")
        assert "verdict" in m.negative_control_summary
        assert "baselines" in m.negative_control_summary

    def test_bootstrap_summary(self):
        m = build_review_model(FIXTURES / "quality_bundle_pass")
        assert "verdict" in m.bootstrap_confidence_summary

    def test_portfolio_overlap_summary(self):
        m = build_review_model(FIXTURES / "quality_bundle_pass")
        assert "verdict" in m.portfolio_overlap_risk

    def test_reproducibility_status(self):
        m = build_review_model(FIXTURES / "quality_bundle_pass")
        assert m.reproducibility_status == "PASS"


class TestViewModelMissingOptional:
    def test_empty_directory_no_crash(self):
        with tempfile.TemporaryDirectory() as d:
            m = build_review_model(Path(d))
            assert m.verdict == "UNKNOWN"
            assert m.composite_score == 0.0
            assert m.evidence_completeness == 0.0

    def test_partial_bundle_no_crash(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "manifest.json").write_text(json.dumps({
                "release_hold": "HOLD", "advisory_only": True,
                "human_review_required": True,
            }))
            m = build_review_model(p)
            assert m.verdict == "UNKNOWN"
            assert m.safety_flags["release_hold_is_HOLD"] is True


class TestViewModelDeterministic:
    def test_output_deterministic(self):
        d = FIXTURES / "quality_bundle_pass"
        r1 = review_model_to_json(build_review_model(d))
        r2 = review_model_to_json(build_review_model(d))
        assert r1 == r2

    def test_dict_roundtrip(self):
        m = build_review_model(FIXTURES / "quality_bundle_pass")
        d = review_model_to_dict(m)
        assert d["verdict"] == "PASS"
        assert d["composite_score"] == pytest.approx(0.85)


class TestViewModelAdversarial:
    def test_corrupted_json_no_crash(self):
        m = build_review_model(FIXTURES / "quality_bundle_corrupted_json")
        assert m.verdict == "UNKNOWN"

    def test_coverage_ratio(self):
        m = build_review_model(FIXTURES / "quality_bundle_pass")
        assert 0.0 <= m.required_artifact_coverage <= 1.0
