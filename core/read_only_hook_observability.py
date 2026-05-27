"""Read-only hook observability — pure frozen dataclasses, no I/O."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

OBSERVATION_POINTS = [
    "hook_invocation",
    "permission_check",
    "invariant_check",
    "sanitization",
    "output_generation",
]


@dataclass(frozen=True)
class ObservabilityEvent:
    event_id: str
    observation_point: str
    hook_id: str
    status: str
    details: Dict[str, Any]


def build_observability_event(
    event_id: str,
    observation_point: str,
    hook_id: str,
    status: str,
    details: Dict[str, Any],
) -> ObservabilityEvent:
    if observation_point not in OBSERVATION_POINTS:
        raise ValueError(f"Invalid observation_point: {observation_point!r}")
    return ObservabilityEvent(
        event_id=event_id,
        observation_point=observation_point,
        hook_id=hook_id,
        status=status,
        details=dict(details),
    )


def observability_event_to_dict(ev: ObservabilityEvent) -> dict:
    return {
        "event_id": ev.event_id,
        "observation_point": ev.observation_point,
        "hook_id": ev.hook_id,
        "status": ev.status,
        "details": dict(ev.details),
    }
