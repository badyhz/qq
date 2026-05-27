"""Tests for read-only hook observability — pure pytest, no I/O."""
import pytest

from core.read_only_hook_observability import (
    OBSERVATION_POINTS,
    ObservabilityEvent,
    build_observability_event,
    observability_event_to_dict,
)


class TestObservability:
    def test_observation_points(self):
        assert len(OBSERVATION_POINTS) == 5
        assert "hook_invocation" in OBSERVATION_POINTS
        assert "permission_check" in OBSERVATION_POINTS
        assert "invariant_check" in OBSERVATION_POINTS
        assert "sanitization" in OBSERVATION_POINTS
        assert "output_generation" in OBSERVATION_POINTS

    def test_build_event(self):
        ev = build_observability_event(
            event_id="ev_01",
            observation_point="hook_invocation",
            hook_id="h1",
            status="ok",
            details={"key": "val"},
        )
        assert isinstance(ev, ObservabilityEvent)
        assert ev.observation_point == "hook_invocation"
        with pytest.raises(ValueError, match="Invalid observation_point"):
            build_observability_event("ev_02", "bad_point", "h1", "ok", {})

    def test_deterministic(self):
        ev = build_observability_event(
            "ev_03", "sanitization", "h2", "ok", {"a": 1}
        )
        d1 = observability_event_to_dict(ev)
        d2 = observability_event_to_dict(ev)
        assert d1 == d2
