"""T1115 - Freeze-Aware Dependency Result."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FreezeAwareDependencyResult:
    """Immutable dependency validation result.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    valid: bool
    missing_deps: tuple[str, ...]
    cycle_detected: bool
    orphans: tuple[str, ...]


def build_dependency_result(
    valid: bool,
    missing_deps: tuple[str, ...] = (),
    cycle_detected: bool = False,
    orphans: tuple[str, ...] = (),
) -> FreezeAwareDependencyResult:
    """Factory for FreezeAwareDependencyResult."""
    return FreezeAwareDependencyResult(
        valid=valid,
        missing_deps=tuple(missing_deps),
        cycle_detected=cycle_detected,
        orphans=tuple(orphans),
    )
