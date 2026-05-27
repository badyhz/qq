"""T1456 - Tests for promotion readiness score, dimension, and calculator."""
from __future__ import annotations

import pytest

from core.promotion_readiness_calculator import calculate_readiness
from core.promotion_readiness_dimension import (
    PromotionReadinessDimension,
    ReadinessDimensionName,
)
from core.promotion_readiness_score import PromotionReadinessScore


# ── Score frozen dataclass ──────────────────────────────────────────────


def test_score_frozen_immutable():
    score = PromotionReadinessScore(
        score_id="s1",
        file_path="core/foo.py",
        dimensions=(),
        overall_score=1.0,
        threshold=0.75,
        is_ready=True,
    )
    with pytest.raises(AttributeError):
        score.score_id = "s2"  # type: ignore[misc]


def test_score_fields():
    score = PromotionReadinessScore(
        score_id="s1",
        file_path="core/foo.py",
        dimensions=(),
        overall_score=0.9,
        threshold=0.75,
        is_ready=True,
    )
    assert score.score_id == "s1"
    assert score.file_path == "core/foo.py"
    assert score.overall_score == 0.9
    assert score.threshold == 0.75
    assert score.is_ready is True


def test_score_with_dimensions_tuple():
    dim = PromotionReadinessDimension(
        dimension_id="d1",
        name=ReadinessDimensionName.IMPORT_SAFETY,
        weight=1.0,
        score=1.0,
        max_score=1.0,
    )
    score = PromotionReadinessScore(
        score_id="s1",
        file_path="core/foo.py",
        dimensions=(dim,),
        overall_score=1.0,
        threshold=0.75,
        is_ready=True,
    )
    assert len(score.dimensions) == 1
    assert score.dimensions[0].name == ReadinessDimensionName.IMPORT_SAFETY


# ── Dimension frozen dataclass ──────────────────────────────────────────


def test_dimension_frozen_immutable():
    dim = PromotionReadinessDimension(
        dimension_id="d1",
        name=ReadinessDimensionName.NETWORK_SAFETY,
        weight=0.2,
        score=1.0,
        max_score=1.0,
    )
    with pytest.raises(AttributeError):
        dim.score = 0.5  # type: ignore[misc]


def test_dimension_all_enum_values():
    expected = {
        "IMPORT_SAFETY",
        "NETWORK_SAFETY",
        "CREDENTIAL_SAFETY",
        "SIDE_EFFECT_SAFETY",
        "DRY_RUN_PROOF",
        "HUMAN_APPROVAL",
        "ROLLBACK_PLAN",
    }
    actual = {v.value for v in ReadinessDimensionName}
    assert actual == expected


def test_dimension_weight_score_ratio():
    dim = PromotionReadinessDimension(
        dimension_id="d1",
        name=ReadinessDimensionName.DRY_RUN_PROOF,
        weight=0.10,
        score=0.8,
        max_score=1.0,
    )
    assert dim.score / dim.max_score == pytest.approx(0.8)


# ── Calculator ──────────────────────────────────────────────────────────


def test_calculator_returns_frozen_score():
    score = calculate_readiness("core/foo.py", "MEDIUM")
    assert isinstance(score, PromotionReadinessScore)
    with pytest.raises(AttributeError):
        score.is_ready = False  # type: ignore[misc]


def test_calculator_high_threshold_higher_than_medium():
    high = calculate_readiness("core/foo.py", "HIGH")
    medium = calculate_readiness("core/bar.py", "MEDIUM")
    assert high.threshold > medium.threshold


def test_calculator_low_threshold_lowest():
    low = calculate_readiness("core/foo.py", "LOW")
    medium = calculate_readiness("core/bar.py", "MEDIUM")
    high = calculate_readiness("core/baz.py", "HIGH")
    assert low.threshold < medium.threshold < high.threshold


def test_calculator_default_baseline_is_ready():
    """Default calculator gives max score on all dims, so is_ready for any risk."""
    for risk in ("HIGH", "MEDIUM", "LOW"):
        score = calculate_readiness("core/x.py", risk)
        assert score.is_ready is True, f"baseline should be ready for {risk}"


def test_calculator_seven_dimensions():
    score = calculate_readiness("core/foo.py", "MEDIUM")
    assert len(score.dimensions) == 7


def test_calculator_dimension_names_complete():
    score = calculate_readiness("core/foo.py", "MEDIUM")
    names = {d.name for d in score.dimensions}
    assert names == set(ReadinessDimensionName)


def test_calculator_weights_sum_to_one():
    score = calculate_readiness("core/foo.py", "MEDIUM")
    total = sum(d.weight for d in score.dimensions)
    assert total == pytest.approx(1.0)


def test_calculator_deterministic():
    a = calculate_readiness("core/foo.py", "HIGH")
    b = calculate_readiness("core/foo.py", "HIGH")
    assert a.overall_score == b.overall_score
    assert a.threshold == b.threshold
    assert a.is_ready == b.is_ready


def test_calculator_unknown_risk_defaults_medium():
    score = calculate_readiness("core/foo.py", "UNKNOWN")
    medium = calculate_readiness("core/bar.py", "MEDIUM")
    assert score.threshold == medium.threshold


def test_calculator_is_ready_false_when_below_threshold():
    """Manually build a score where overall < threshold to verify is_ready logic."""
    dim = PromotionReadinessDimension(
        dimension_id="d1",
        name=ReadinessDimensionName.IMPORT_SAFETY,
        weight=1.0,
        score=0.5,
        max_score=1.0,
    )
    score = PromotionReadinessScore(
        score_id="s1",
        file_path="core/foo.py",
        dimensions=(dim,),
        overall_score=0.5,
        threshold=0.90,
        is_ready=False,
    )
    assert score.is_ready is False
    assert score.overall_score < score.threshold
