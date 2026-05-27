"""T1117 - Freeze-Aware Hold State."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FreezeAwareHoldState:
    """Immutable hold state.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    hold_active: bool
    hold_reason: str
    blocked_task_ids: tuple[str, ...]
    release_requires_human: bool


def build_hold_state(
    hold_active: bool,
    hold_reason: str = "",
    blocked_task_ids: tuple[str, ...] = (),
    release_requires_human: bool = False,
) -> FreezeAwareHoldState:
    """Factory for FreezeAwareHoldState."""
    return FreezeAwareHoldState(
        hold_active=hold_active,
        hold_reason=hold_reason,
        blocked_task_ids=tuple(blocked_task_ids),
        release_requires_human=release_requires_human,
    )
