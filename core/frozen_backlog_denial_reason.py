"""T1304 - Frozen Backlog Denial Reason."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrozenBacklogDenialReason:
    """Immutable denial reason.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    reason_id: str
    category: str
    description: str
    severity: str

    def to_dict(self) -> dict[str, str]:
        return {
            "reason_id": self.reason_id,
            "category": self.category,
            "description": self.description,
            "severity": self.severity,
        }


def build_denial_reason(
    reason_id: str,
    category: str,
    description: str,
    severity: str = "MEDIUM",
) -> FrozenBacklogDenialReason:
    """Factory for FrozenBacklogDenialReason."""
    return FrozenBacklogDenialReason(
        reason_id=reason_id,
        category=category,
        description=description,
        severity=severity,
    )


def denial_reason_to_dict(r: FrozenBacklogDenialReason) -> dict[str, str]:
    """Convert denial reason to a plain dict."""
    return r.to_dict()
