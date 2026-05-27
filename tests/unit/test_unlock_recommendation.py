"""T1465 - Tests for UnlockRecommendation, engine, and renderer."""
from __future__ import annotations

import pytest

from core.unlock_recommendation import UnlockRecommendation
from core.unlock_recommendation_engine import generate_unlock_recommendation
from core.unlock_recommendation_renderer import (
    render_unlock_recommendation_md,
    render_recommendation_conditions_md,
    render_recommendation_blockers_md,
)


# --- Frozen dataclass tests ---

def test_unlock_recommendation_frozen() -> None:
    rec = UnlockRecommendation(
        recommendation_id="r1",
        file_path="a.py",
        risk_class="HIGH",
        readiness_score=0.95,
        recommendation="PROMOTE",
        conditions=("c1",),
        blockers=(),
    )
    with pytest.raises(AttributeError):
        rec.recommendation_id = "changed"  # type: ignore[misc]


def test_unlock_recommendation_fields() -> None:
    rec = UnlockRecommendation(
        recommendation_id="r1",
        file_path="a.py",
        risk_class="HIGH",
        readiness_score=0.95,
        recommendation="PROMOTE",
        conditions=("c1",),
        blockers=("b1",),
    )
    assert rec.recommendation_id == "r1"
    assert rec.file_path == "a.py"
    assert rec.risk_class == "HIGH"
    assert rec.readiness_score == 0.95
    assert rec.recommendation == "PROMOTE"
    assert rec.conditions == ("c1",)
    assert rec.blockers == ("b1",)


def test_unlock_recommendation_class_constants() -> None:
    assert UnlockRecommendation.HOLD == "HOLD"
    assert UnlockRecommendation.PROMOTE == "PROMOTE"
    assert UnlockRecommendation.DEFER == "DEFER"
    assert UnlockRecommendation.REJECT == "REJECT"


# --- Engine tests ---

def test_engine_high_below_threshold_is_hold() -> None:
    rec = generate_unlock_recommendation(
        file_path="x.py", risk_class="HIGH", readiness_score=0.5
    )
    assert rec.recommendation == "HOLD"
    assert len(rec.blockers) > 0


def test_engine_high_above_threshold_is_promote() -> None:
    rec = generate_unlock_recommendation(
        file_path="x.py", risk_class="HIGH", readiness_score=0.95
    )
    assert rec.recommendation == "PROMOTE"


def test_engine_high_exactly_threshold_is_promote() -> None:
    rec = generate_unlock_recommendation(
        file_path="x.py", risk_class="HIGH", readiness_score=0.9
    )
    assert rec.recommendation == "PROMOTE"


def test_engine_medium_below_threshold_is_hold() -> None:
    rec = generate_unlock_recommendation(
        file_path="y.py", risk_class="MEDIUM", readiness_score=0.3
    )
    assert rec.recommendation == "HOLD"
    assert len(rec.blockers) > 0


def test_engine_medium_above_threshold_is_promote() -> None:
    rec = generate_unlock_recommendation(
        file_path="y.py", risk_class="MEDIUM", readiness_score=0.8
    )
    assert rec.recommendation == "PROMOTE"


def test_engine_low_below_threshold_is_defer() -> None:
    rec = generate_unlock_recommendation(
        file_path="z.py", risk_class="LOW", readiness_score=0.2
    )
    assert rec.recommendation == "DEFER"


def test_engine_low_above_threshold_is_promote() -> None:
    rec = generate_unlock_recommendation(
        file_path="z.py", risk_class="LOW", readiness_score=0.8
    )
    assert rec.recommendation == "PROMOTE"


def test_engine_unknown_risk_is_reject() -> None:
    rec = generate_unlock_recommendation(
        file_path="w.py", risk_class="UNKNOWN", readiness_score=0.9
    )
    assert rec.recommendation == "REJECT"


def test_engine_output_is_frozen() -> None:
    rec = generate_unlock_recommendation(
        file_path="a.py", risk_class="HIGH", readiness_score=0.5
    )
    with pytest.raises(AttributeError):
        rec.recommendation = "PROMOTE"  # type: ignore[misc]


def test_engine_deterministic() -> None:
    args = dict(file_path="a.py", risk_class="HIGH", readiness_score=0.5)
    r1 = generate_unlock_recommendation(**args)
    r2 = generate_unlock_recommendation(**args)
    assert r1 == r2


# --- Renderer tests ---

def test_renderer_full_md() -> None:
    rec = generate_unlock_recommendation(
        file_path="a.py", risk_class="HIGH", readiness_score=0.5
    )
    md = render_unlock_recommendation_md(rec)
    assert "Unlock Recommendation" in md
    assert "a.py" in md
    assert "HOLD" in md


def test_renderer_conditions_md() -> None:
    rec = generate_unlock_recommendation(
        file_path="a.py", risk_class="HIGH", readiness_score=0.5
    )
    md = render_recommendation_conditions_md(rec)
    assert "Conditions" in md
    assert "achieve_readiness_score_above_0.9" in md


def test_renderer_blockers_md() -> None:
    rec = generate_unlock_recommendation(
        file_path="a.py", risk_class="HIGH", readiness_score=0.5
    )
    md = render_recommendation_blockers_md(rec)
    assert "Blockers" in md
    assert "readiness_score_below_0.9_for_HIGH_risk" in md
