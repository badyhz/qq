"""T1120 - Freeze-Aware Queue Model Closeout."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FreezeAwareQueueModelCloseout:
    """Immutable closeout aggregation.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    model_count: int
    models: tuple[str, ...]
    verdict: str


def build_closeout(
    models: tuple[str, ...] = (),
    verdict: str = "PASS",
) -> FreezeAwareQueueModelCloseout:
    """Factory for FreezeAwareQueueModelCloseout."""
    return FreezeAwareQueueModelCloseout(
        model_count=len(tuple(models)),
        models=tuple(models),
        verdict=verdict,
    )


def closeout_to_dict(c: FreezeAwareQueueModelCloseout) -> dict:
    """Convert closeout to a plain dict."""
    return {
        "model_count": c.model_count,
        "models": list(c.models),
        "verdict": c.verdict,
    }
