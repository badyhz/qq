"""Tests for research quality score — T8001-T8040.

Weighted score, missing evidence, hard block tests.
"""
from __future__ import annotations

import pytest
from core.research_quality_score import (
    compute_composite_score, compute_evidence_completeness,
    build_quality_gate_summary,
)


class TestQualityScoreNormal:
    def test_composite_score(self):
        scores = {"data_quality": 1.0, "split": 0.8, "param": 0.9}
        score = compute_composite_score(scores)
        assert 0.8 < score < 1.0

    def test_evidence_completeness(self):
        completeness = compute_evidence_completeness(
            ["a.json", "b.json", "c.json"],
            ["a.json", "b.json"],
        )
        assert abs(completeness - 2 / 3) < 0.01

    def test_build_summary(self):
        summary = build_quality_gate_summary(
            {"a": 0.8}, ["a.json"], ["a.json"], [], [], seed=42
        )
        assert summary["verdict"] == "PASS"


class TestQualityScoreEdge:
    def test_empty_scores(self):
        assert compute_composite_score({}) == 0.0

    def test_empty_evidence(self):
        assert compute_evidence_completeness([], []) == 1.0


class TestQualityScoreAdversarial:
    def test_hard_blocks_fail(self):
        summary = build_quality_gate_summary(
            {"a": 0.8}, [], ["a.json"], ["BLOCK"], [], seed=42
        )
        assert summary["verdict"] == "FAIL"

    def test_low_completeness_partial(self):
        summary = build_quality_gate_summary(
            {"a": 0.8}, [], ["a.json", "b.json", "c.json"], [], [], seed=42
        )
        assert summary["verdict"] == "PARTIAL"


class TestQualityScoreSafetyBoundary:
    def test_summary_safety(self):
        summary = build_quality_gate_summary({}, [], [], [], [], seed=42)
        assert summary["release_hold"] == "HOLD"
        assert summary["advisory_only"] is True
        assert summary["human_review_required"] is True
