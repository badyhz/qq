"""T1113 - Freeze-Aware Admission Result."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FreezeAwareAdmissionResult:
    """Immutable admission decision.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    admitted: bool
    task_id: str
    reason: str
    blocking_freeze_files: tuple[str, ...]


def build_admission_result(
    admitted: bool,
    task_id: str,
    reason: str,
    blocking_freeze_files: tuple[str, ...] = (),
) -> FreezeAwareAdmissionResult:
    """Factory for FreezeAwareAdmissionResult."""
    return FreezeAwareAdmissionResult(
        admitted=admitted,
        task_id=task_id,
        reason=reason,
        blocking_freeze_files=tuple(blocking_freeze_files),
    )
