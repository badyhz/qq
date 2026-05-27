"""T1315 — Medium operational deny-submit model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediumOperationalDenySubmitModel:
    """Declares operations that must never be submitted in medium-risk context."""

    model_id: str
    denied_operations: tuple[str, ...]
    severity: str

    def is_operation_denied(self, operation: str) -> bool:
        return operation in self.denied_operations

    def denied_count(self) -> int:
        return len(self.denied_operations)

    def denied_set(self) -> frozenset[str]:
        return frozenset(self.denied_operations)

    def is_critical(self) -> bool:
        return self.severity == "CRITICAL"

    def is_high(self) -> bool:
        return self.severity == "HIGH"

    def is_medium(self) -> bool:
        return self.severity == "MEDIUM"

    def severity_rank(self) -> int:
        ranks = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}
        return ranks.get(self.severity, -1)
