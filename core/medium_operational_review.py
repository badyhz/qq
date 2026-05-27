"""T1311 — Medium operational review aggregate model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediumOperationalReview:
    """Aggregates scripts, policies, and verdict for a medium-risk review."""

    review_id: str
    scripts: tuple[str, ...]
    policies: tuple[str, ...]
    verdict: str

    def script_count(self) -> int:
        return len(self.scripts)

    def policy_count(self) -> int:
        return len(self.policies)

    def is_approved(self) -> bool:
        return self.verdict == "APPROVED"

    def is_denied(self) -> bool:
        return self.verdict == "DENIED"

    def has_scripts(self) -> bool:
        return len(self.scripts) > 0

    def has_policies(self) -> bool:
        return len(self.policies) > 0

    def script_set(self) -> frozenset[str]:
        return frozenset(self.scripts)

    def policy_set(self) -> frozenset[str]:
        return frozenset(self.policies)
