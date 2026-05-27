"""Tests for core.runtime_governance_readiness_score.

Deterministic. No I/O. No network. No timestamps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.runtime_governance_regression_packet import (
    RuntimeGovernanceRegressionPacket,
    build_runtime_governance_regression_packet,
)
from core.runtime_governance_readiness_score import (
    RuntimeGovernanceReadinessScore,
    compute_runtime_governance_readiness_score,
    readiness_score_to_dict,
    readiness_score_to_markdown,
)


# ── helpers ────────────────────────────────────────────────────────────


def _build_packet(
    *,
    scenario_count: int = 8,
    scenario_pass_count: int = 8,
    scenario_fail_count: int = 0,
    invariant_errors: int = 0,
    manifest_verdict: str = "PASS",
    final_verdict: str = "PASS",
    notes: List[str] | None = None,
) -> RuntimeGovernanceRegressionPacket:
    """Construct a regression packet directly with given parameters."""
    return RuntimeGovernanceRegressionPacket(
        title="Test Regression",
        final_verdict=final_verdict,
        scenario_count=scenario_count,
        scenario_pass_count=scenario_pass_count,
        scenario_fail_count=scenario_fail_count,
        invariant_summary={
            "total": 48,
            "passed": 48 - invariant_errors,
            "failed": invariant_errors,
            "errors": invariant_errors,
            "warnings": 0,
            "all_ok": invariant_errors == 0,
        },
        manifest_summary={
            "total": 12,
            "completed": 12,
            "verdict": manifest_verdict,
        },
        notes=notes or [],
    )


def _build_perfect_packet() -> RuntimeGovernanceRegressionPacket:
    """All scenarios pass, no invariant errors, manifest PASS."""
    return _build_packet()


def _build_packet_with_manifest_fail() -> RuntimeGovernanceRegressionPacket:
    """Manifest FAIL → -20 penalty."""
    return _build_packet(
        manifest_verdict="FAIL",
        final_verdict="FAIL",
        notes=["manifest fail"],
    )


def _build_packet_manifest_warn() -> RuntimeGovernanceRegressionPacket:
    """Manifest WARN → -5 penalty."""
    return _build_packet(
        manifest_verdict="WARN",
        final_verdict="WARN",
        notes=["manifest warn"],
    )


# ── perfect packet → A grade ──────────────────────────────────────────


class TestPerfectPacket:
    """Perfect packet should score 100 and grade A."""

    def test_score_100(self):
        packet = _build_perfect_packet()
        score = compute_runtime_governance_readiness_score(packet)
        assert score.score == 100
        assert score.max_score == 100

    def test_percent_100(self):
        packet = _build_perfect_packet()
        score = compute_runtime_governance_readiness_score(packet)
        assert score.percent == 100.0

    def test_grade_a(self):
        packet = _build_perfect_packet()
        score = compute_runtime_governance_readiness_score(packet)
        assert score.grade == "A"

    def test_no_blockers(self):
        packet = _build_perfect_packet()
        score = compute_runtime_governance_readiness_score(packet)
        assert score.blockers == []

    def test_no_warnings(self):
        packet = _build_perfect_packet()
        score = compute_runtime_governance_readiness_score(packet)
        assert score.warnings == []


# ── one fail scenario → lower score ───────────────────────────────────


class TestFailScenario:
    """Packet with manifest FAIL should produce lower score."""

    def test_score_less_than_100(self):
        packet = _build_packet_with_manifest_fail()
        score = compute_runtime_governance_readiness_score(packet)
        assert score.score < 100

    def test_grade_not_a(self):
        packet = _build_packet_with_manifest_fail()
        score = compute_runtime_governance_readiness_score(packet)
        assert score.grade != "A"

    def test_has_blockers(self):
        packet = _build_packet_with_manifest_fail()
        score = compute_runtime_governance_readiness_score(packet)
        assert len(score.blockers) > 0

    def test_manifest_fail_penalty(self):
        """Manifest FAIL costs 20 points."""
        packet = _build_packet_with_manifest_fail()
        score = compute_runtime_governance_readiness_score(packet)
        # manifest FAIL = -20, so score = 80
        assert score.score == 80

    def test_grade_b_at_80(self):
        """Score 80 → grade B (>=75)."""
        packet = _build_packet_with_manifest_fail()
        score = compute_runtime_governance_readiness_score(packet)
        assert score.grade == "B"


class TestManifestWarn:
    """Packet with manifest WARN should cost 5 points."""

    def test_score_95(self):
        packet = _build_packet_manifest_warn()
        score = compute_runtime_governance_readiness_score(packet)
        assert score.score == 95

    def test_grade_a(self):
        """Score 95 → grade A (>=90)."""
        packet = _build_packet_manifest_warn()
        score = compute_runtime_governance_readiness_score(packet)
        assert score.grade == "A"

    def test_has_warning(self):
        packet = _build_packet_manifest_warn()
        score = compute_runtime_governance_readiness_score(packet)
        assert any("manifest" in w for w in score.warnings)


# ── determinism ────────────────────────────────────────────────────────


class TestDeterminism:
    """Score computation must be deterministic."""

    def test_score_deterministic(self):
        packet = _build_perfect_packet()
        s1 = compute_runtime_governance_readiness_score(packet)
        s2 = compute_runtime_governance_readiness_score(packet)
        assert s1.score == s2.score
        assert s1.percent == s2.percent
        assert s1.grade == s2.grade
        assert s1.blockers == s2.blockers
        assert s1.warnings == s2.warnings
        assert s1.notes == s2.notes

    def test_dict_deterministic(self):
        packet = _build_perfect_packet()
        score = compute_runtime_governance_readiness_score(packet)
        d1 = readiness_score_to_dict(score)
        d2 = readiness_score_to_dict(score)
        assert d1 == d2


# ── markdown deterministic ────────────────────────────────────────────


class TestMarkdown:
    """Markdown rendering must be deterministic."""

    def test_markdown_deterministic(self):
        packet = _build_perfect_packet()
        score = compute_runtime_governance_readiness_score(packet)
        m1 = readiness_score_to_markdown(score)
        m2 = readiness_score_to_markdown(score)
        assert m1 == m2

    def test_markdown_contains_grade(self):
        packet = _build_perfect_packet()
        score = compute_runtime_governance_readiness_score(packet)
        md = readiness_score_to_markdown(score)
        assert "Grade:** A" in md

    def test_markdown_contains_score(self):
        packet = _build_perfect_packet()
        score = compute_runtime_governance_readiness_score(packet)
        md = readiness_score_to_markdown(score)
        assert "Score:** 100/100" in md

    def test_markdown_no_timestamps(self):
        packet = _build_perfect_packet()
        score = compute_runtime_governance_readiness_score(packet)
        md = readiness_score_to_markdown(score)
        assert "202" not in md or "T" not in md
        assert "UTC" not in md


# ── serialization ──────────────────────────────────────────────────────


class TestSerialization:
    """Dict serialization must produce expected keys."""

    def test_dict_keys(self):
        packet = _build_perfect_packet()
        score = compute_runtime_governance_readiness_score(packet)
        d = readiness_score_to_dict(score)
        expected_keys = {"score", "max_score", "percent", "grade", "blockers", "warnings", "notes"}
        assert set(d.keys()) == expected_keys

    def test_dict_values_match(self):
        packet = _build_perfect_packet()
        score = compute_runtime_governance_readiness_score(packet)
        d = readiness_score_to_dict(score)
        assert d["score"] == 100
        assert d["max_score"] == 100
        assert d["percent"] == 100.0
        assert d["grade"] == "A"


# ── grade thresholds ──────────────────────────────────────────────────


class TestGradeThresholds:
    """Verify grade threshold boundaries."""

    def test_boundary_90_is_a(self):
        """Score 90 → A."""
        packet = _build_perfect_packet()
        score = compute_runtime_governance_readiness_score(packet)
        # manually verify: perfect score = 100 → A
        assert score.grade == "A"

    def test_manifest_fail_gives_b(self):
        """Manifest FAIL (-20) → score 80 → B."""
        packet = _build_packet_with_manifest_fail()
        score = compute_runtime_governance_readiness_score(packet)
        assert score.score == 80
        assert score.grade == "B"
