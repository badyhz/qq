from __future__ import annotations

import pytest

from core.implementation_readiness_scoring import ImplementationReadinessScoring
from core.readiness_score_dimension import ReadinessScoreDimension
from core.readiness_blocker import ReadinessBlocker, BlockerType, BlockerSeverity
from core.readiness_scoring_verdict import ReadinessScoringVerdict, VerdictValue


class TestImplementationReadinessScoring:
    def test_create_scoring_frozen(self) -> None:
        v = ReadinessScoringVerdict(
            verdict=VerdictValue.PASS,
            score_pct=100.0,
            blockers=(),
            notes="ok",
        )
        s = ImplementationReadinessScoring(
            scoring_id="RS-001",
            dimensions=(),
            blockers=(),
            hold_state=False,
            verdict=v,
        )
        assert s.scoring_id == "RS-001"
        with pytest.raises(AttributeError):
            s.scoring_id = "X"  # type: ignore[misc]

    def test_scoring_with_dimensions(self) -> None:
        dims = (ReadinessScoreDimension.TEST_COVERAGE, ReadinessScoreDimension.SAFETY_BOUNDARY)
        v = ReadinessScoringVerdict(
            verdict=VerdictValue.HOLD,
            score_pct=50.0,
            blockers=(),
            notes="partial",
        )
        s = ImplementationReadinessScoring(
            scoring_id="RS-002",
            dimensions=dims,
            blockers=(),
            hold_state=True,
            verdict=v,
        )
        assert len(s.dimensions) == 2


class TestReadinessScoreDimension:
    def test_all_dimensions_exist(self) -> None:
        expected = (
            "TEST_COVERAGE", "DOCUMENTATION", "SAFETY_BOUNDARY",
            "HUMAN_APPROVAL", "DEPENDENCY_RESOLUTION", "REGRESSION_RISK",
        )
        for name in expected:
            dim = ReadinessScoreDimension(name)
            assert dim.value == name

    def test_weights_sum_to_one(self) -> None:
        total = sum(d.weight() for d in ReadinessScoreDimension)
        assert abs(total - 1.0) < 1e-9

    def test_thresholds_valid(self) -> None:
        for d in ReadinessScoreDimension:
            t = d.threshold()
            assert 0.0 <= t <= 1.0

    def test_weight_values(self) -> None:
        assert ReadinessScoreDimension.TEST_COVERAGE.weight() == 0.25
        assert ReadinessScoreDimension.SAFETY_BOUNDARY.weight() == 0.25
        assert ReadinessScoreDimension.REGRESSION_RISK.weight() == 0.10


class TestReadinessBlocker:
    def test_create_blocker_frozen(self) -> None:
        b = ReadinessBlocker(
            blocker_id="B-001",
            blocker_type=BlockerType.MISSING_TESTS,
            severity=BlockerSeverity.HIGH,
            description="test gap",
            resolution_path="add tests",
        )
        assert b.blocker_id == "B-001"
        with pytest.raises(AttributeError):
            b.blocker_id = "X"  # type: ignore[misc]

    def test_blocker_types(self) -> None:
        assert BlockerType.MISSING_TESTS.value == "MISSING_TESTS"
        assert BlockerType.SAFETY_VIOLATION.value == "SAFETY_VIOLATION"

    def test_blocker_severity(self) -> None:
        assert BlockerSeverity.CRITICAL.value == "CRITICAL"
        assert BlockerSeverity.MEDIUM.value == "MEDIUM"
