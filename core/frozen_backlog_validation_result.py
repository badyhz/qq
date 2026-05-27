"""T1602 - Frozen Backlog Validation Result.

Frozen dataclass for report validation outcome.
Pure deterministic. No I/O. No timestamps. No network.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrozenBacklogValidationResult:
    """Immutable validation result.

    Pure frozen. No I/O. No timestamps. No network.
    """

    is_valid: bool
    checks_passed: tuple[str, ...]
    checks_failed: tuple[str, ...]
    error_message: str


def build_validation_result(
    is_valid: bool,
    checks_passed: tuple[str, ...],
    checks_failed: tuple[str, ...],
    error_message: str = "",
) -> FrozenBacklogValidationResult:
    """Build a FrozenBacklogValidationResult. Pure function."""
    return FrozenBacklogValidationResult(
        is_valid=is_valid,
        checks_passed=checks_passed,
        checks_failed=checks_failed,
        error_message=error_message,
    )
